import json
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from functools import wraps
import jwt
import logging

logger = logging.getLogger(__name__)

def validate_token(f):
    """Decorator para validar JWT token"""
    @wraps(f)
    def decorated_function(request, *args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        
        try:
            # Validar token
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=['HS256']
            )
            request.user_id = payload.get('user_id')
            request.user_role = payload.get('role')
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expirado'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Token inválido'}, status=401)
        
        return f(request, *args, **kwargs)
    
    return decorated_function

@csrf_exempt
def proxy_to_auth(request):
    """Proxy requests para o serviço de autenticação"""
    auth_url = f"{settings.MICROSERVICES['AUTH_SERVICE']}{request.path.replace('/api', '')}"
    
    try:
        # Preparar headers
        headers = {
            'Content-Type': request.headers.get('Content-Type', 'application/json'),
            'X-Forwarded-For': request.META.get('REMOTE_ADDR'),
            'X-Request-ID': request.headers.get('X-Request-ID', ''),
        }
        
        # Adicionar token se existir
        auth_header = request.headers.get('Authorization')
        if auth_header:
            headers['Authorization'] = auth_header
        
        # Fazer proxy da requisição
        if request.method == 'GET':
            response = requests.get(auth_url, headers=headers, params=request.GET)
        elif request.method == 'POST':
            response = requests.post(auth_url, headers=headers, data=request.body)
        elif request.method == 'PUT':
            response = requests.put(auth_url, headers=headers, data=request.body)
        elif request.method == 'DELETE':
            response = requests.delete(auth_url, headers=headers)
        else:
            return JsonResponse({'error': 'Método não permitido'}, status=405)
        
        # Retornar resposta
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao conectar com auth-service: {e}")
        return JsonResponse(
            {'error': 'Serviço de autenticação indisponível'}, 
            status=503
        )

@csrf_exempt
@validate_token
def proxy_to_tasks(request, task_id=None):
    """Proxy requests para o serviço de tarefas"""
    # Construir URL
    path = request.path.replace('/api', '')
    if task_id:
        path = path.replace('<str:task_id>', task_id)
    
    task_url = f"{settings.MICROSERVICES['TASK_SERVICE']}{path}"
    
    try:
        # Preparar headers
        headers = {
            'Content-Type': request.headers.get('Content-Type', 'application/json'),
            'X-User-ID': str(request.user_id),
            'X-User-Role': request.user_role,
            'X-Forwarded-For': request.META.get('REMOTE_ADDR'),
        }
        
        # Fazer proxy da requisição
        if request.method == 'GET':
            response = requests.get(task_url, headers=headers, params=request.GET)
        elif request.method == 'POST':
            response = requests.post(task_url, headers=headers, data=request.body)
        elif request.method == 'PUT':
            response = requests.put(task_url, headers=headers, data=request.body)
        elif request.method == 'DELETE':
            response = requests.delete(task_url, headers=headers)
        else:
            return JsonResponse({'error': 'Método não permitido'}, status=405)
        
        # Retornar resposta
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao conectar com task-service: {e}")
        return JsonResponse(
            {'error': 'Serviço de tarefas indisponível'}, 
            status=503
        )

@csrf_exempt
@validate_token
def admin_proxy(request):
    """Proxy para rotas administrativas com validação extra"""
    # Verificar se é admin
    if request.user_role != 'ADMIN':
        return JsonResponse({'error': 'Acesso negado'}, status=403)
    
    # Determinar qual serviço usar baseado no path
    if '/users' in request.path:
        return proxy_to_auth(request)
    else:
        return proxy_to_tasks(request)