from rest_framework import serializers
from .models import Task, TaskNotification, TaskAttachment

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'priority', 'status',
                 'due_date', 'progress', 'tags', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TaskDetailSerializer(TaskSerializer):
    attachments = serializers.SerializerMethodField()
    history_count = serializers.SerializerMethodField()
    
    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['completed_at', 'attachments', 'history_count']
    
    def get_attachments(self, obj):
        return [{
            'id': str(att.id),
            'filename': att.filename,
            'size': att.file_size,
            'uploaded_at': att.uploaded_at
        } for att in obj.attachments.all()]
    
    def get_history_count(self, obj):
        return obj.history.count()

class NotificationSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskNotification
        fields = ['id', 'task', 'task_title', 'notification_type',
                 'message', 'is_read', 'created_at', 'read_at']
        read_only_fields = ['id', 'created_at']