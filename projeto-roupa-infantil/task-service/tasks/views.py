from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .models import Task, TaskHistory, TaskNotification, TaskAttachment
from .serializers import TaskSerializer, TaskDetailSerializer, NotificationSerializer
import os
from django.conf import settings
from django.core.files.storage import default_storage

def create_task_history(task, user_id, action, changes=None):
    TaskHistory.objects.create(
        task=task,
        user_id=user_id,
        action=action,
        changes=changes or {}
    )

def create_notification(task, user_id, notification_type, message):
    TaskNotification.objects.create(
        task=task,
        user_id=user_id,
        notification_type=notification_type,
        message=message
    )

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def tasks_list(request):
    user_id = request.headers.get('X-User-ID')
    user_role = request.headers.get('X-User-Role')
    
    if request.method == 'GET':
        # Filtros
        status_filter = request.GET.get('status')
        priority_filter = request.GET.get('priority')
        search = request.GET.get('search')
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 20)
        
        # Query base
        if user_role == 'ADMIN':
            tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(user_id=user_id)
        
        # Aplicar filtros
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        if priority_filter:
            tasks = tasks.filter(priority=priority_filter)
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Paginação
        paginator = Paginator(tasks, per_page)
        page_obj = paginator.get_page(page)
        
        # Serializar
        serializer = TaskSerializer(page_obj, many=True)
        
        return Response({
            'tasks': serializer.data,
            'total': paginator.count,
            'pages': paginator.num_pages,
            'current_page': int(page),
            'per_page': int(per_page)
        })
    
    elif request.method == 'POST':
        serializer = TaskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar tarefa
        task = serializer.save(user_id=user_id)
        
        # Histórico
        create_task_history(task, user_id, 'CREATED')
        
        # Notificação
        create_notification(
            task, 
            user_id, 
            'ASSIGNED', 
            f'Nova tarefa criada: {task.title}'
        )
        
        return Response(
            TaskDetailSerializer(task).data, 
            status=status.HTTP_201_CREATED
        )

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def task_detail(request, task_id):
    user_id = request.headers.get('X-User-ID')
    user_role = request.headers.get('X-User-Role')
    
    try:
        if user_role == 'ADMIN':
            task = Task.objects.get(id=task_id)
        else:
            task = Task.objects.get(id=task_id, user_id=user_id)
    except Task.DoesNotExist:
        return Response({
            'error': 'Tarefa não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TaskDetailSerializer(task)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Guardar estado anterior
        old_data = TaskSerializer(task).data
        
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar mudanças especiais
        if 'status' in request.data:
            if request.data['status'] == 'COMPLETED' and task.status != 'COMPLETED':
                task.completed_at = timezone.now()
                create_notification(
                    task,
                    user_id,
                    'COMPLETED',
                    f'Tarefa concluída: {task.title}'
                )
        
        serializer.save()
        
        # Histórico com mudanças
        changes = {}
        for field in request.data:
            if old_data.get(field) != request.data.get(field):
                changes[field] = {
                    'old': old_data.get(field),
                    'new': request.data.get(field)
                }
        
        if changes:
            create_task_history(task, user_id, 'UPDATED', changes)
        
        return Response(TaskDetailSerializer(task).data)
    
    elif request.method == 'DELETE':
        # Soft delete - marcar como cancelada
        task.status = 'CANCELLED'
        task.save()
        
        create_task_history(task, user_id, 'CANCELLED')
        
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_history(request, task_id):
    user_id = request.headers.get('X-User-ID')
    user_role = request.headers.get('X-User-Role')
    
    try:
        if user_role == 'ADMIN':
            task = Task.objects.get(id=task_id)
        else:
            task = Task.objects.get(id=task_id, user_id=user_id)
    except Task.DoesNotExist:
        return Response({
            'error': 'Tarefa não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)
    
    history = task.history.all()
    
    return Response([{
        'id': str(h.id),
        'action': h.action,
        'changes': h.changes,
        'timestamp': h.timestamp,
        'user_id': str(h.user_id)
    } for h in history])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    user_id = request.headers.get('X-User-ID')
    
    # Filtros
    is_read = request.GET.get('is_read')
    notification_type = request.GET.get('type')
    
    notifications = TaskNotification.objects.filter(user_id=user_id)
    
    if is_read is not None:
        notifications = notifications.filter(is_read=is_read == 'true')
    
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    serializer = NotificationSerializer(notifications, many=True)
    
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    user_id = request.headers.get('X-User-ID')
    
    try:
        notification = TaskNotification.objects.get(
            id=notification_id,
            user_id=user_id
        )
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return Response({'success': True})
    except TaskNotification.DoesNotExist:
        return Response({
            'error': 'Notificação não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports(request, report_type):
    user_id = request.headers.get('X-User-ID')
    user_role = request.headers.get('X-User-Role')
    
    # Período do relatório
    period = request.GET.get('period', 'month')  # week, month, year
    
    # Calcular data inicial
    end_date = timezone.now()
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Query base
    if user_role == 'ADMIN':
        tasks = Task.objects.filter(created_at__range=[start_date, end_date])
    else:
        tasks = Task.objects.filter(
            user_id=user_id,
            created_at__range=[start_date, end_date]
        )
    
    if report_type == 'summary':
        # Relatório resumido
        data = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'total_tasks': tasks.count(),
            'by_status': {},
            'by_priority': {},
            'completion_rate': 0,
            'average_completion_time': None
        }
        
        # Por status
        for status, label in Task.STATUS_CHOICES:
            data['by_status'][status] = tasks.filter(status=status).count()
        
        # Por prioridade
        for priority, label in Task.PRIORITY_CHOICES:
            data['by_priority'][priority] = tasks.filter(priority=priority).count()
        
        # Taxa de conclusão
        completed = tasks.filter(status='COMPLETED').count()
        if tasks.count() > 0:
            data['completion_rate'] = (completed / tasks.count()) * 100
        
        # Tempo médio de conclusão
        completed_tasks = tasks.filter(
            status='COMPLETED',
            completed_at__isnull=False
        )
        if completed_tasks.exists():
            times = []
            for task in completed_tasks:
                duration = (task.completed_at - task.created_at).total_seconds() / 3600
                times.append(duration)
            data['average_completion_time'] = sum(times) / len(times)
        
        return Response(data)
    
    elif report_type == 'productivity':
        # Relatório de produtividade
        data = {
            'period': period,
            'daily_activity': [],
            'peak_hours': {},
            'most_productive_day': None
        }
        
        # Atividade diária
        current = start_date
        while current <= end_date:
            day_tasks = tasks.filter(
                created_at__date=current.date()
            )
            data['daily_activity'].append({
                'date': current.date(),
                'created': day_tasks.count(),
                'completed': day_tasks.filter(status='COMPLETED').count()
            })
            current += timedelta(days=1)
        
        # Horas de pico
        for hour in range(24):
            count = tasks.filter(created_at__hour=hour).count()
            data['peak_hours'][f"{hour:02d}:00"] = count
        
        return Response(data)
    
    else:
        return Response({
            'error': 'Tipo de relatório inválido'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    user_id = request.headers.get('X-User-ID')
    task_id = request.POST.get('task_id')
    file = request.FILES.get('file')
    
    if not task_id or not file:
        return Response({
            'error': 'Task ID e arquivo são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Verificar se a tarefa existe e pertence ao usuário
        task = Task.objects.get(id=task_id, user_id=user_id)
    except Task.DoesNotExist:
        return Response({
            'error': 'Tarefa não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Validar arquivo
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        return Response({
            'error': 'Arquivo muito grande. Máximo: 10MB'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Tipos permitidos
    allowed_types = [
        'image/jpeg', 'image/png', 'image/gif',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain', 'text/csv'
    ]
    
    if file.content_type not in allowed_types:
        return Response({
            'error': 'Tipo de arquivo não permitido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Salvar arquivo
    filename = f"{task_id}/{user_id}/{timezone.now().timestamp()}_{file.name}"
    path = default_storage.save(filename, file)
    
    # Criar registro
    attachment = TaskAttachment.objects.create(
        task=task,
        filename=file.name,
        file_path=path,
        file_size=file.size,
        content_type=file.content_type,
        uploaded_by=user_id
    )
    
    # Histórico
    create_task_history(task, user_id, 'FILE_UPLOADED', {
        'filename': file.name,
        'size': file.size
    })
    
    return Response({
        'id': str(attachment.id),
        'filename': attachment.filename,
        'size': attachment.file_size,
        'uploaded_at': attachment.uploaded_at
    }, status=status.HTTP_201_CREATED)