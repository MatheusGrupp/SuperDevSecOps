from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
import uuid
import secrets

class UserManager(BaseUserManager):
    def create_user(self, email, nome, cpf, password=None):
        if not email:
            raise ValueError('Email é obrigatório')
        if not nome:
            raise ValueError('Nome é obrigatório')
        if not cpf:
            raise ValueError('CPF é obrigatório')
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            nome=nome,
            cpf=cpf
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, nome, cpf, password=None):
        user = self.create_user(email, nome, cpf, password)
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    ROLES = (
        ('USER', 'Usuário'),
        ('ADMIN', 'Administrador'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        max_length=255, 
        unique=True,
        validators=[EmailValidator()]
    )
    nome = models.CharField(max_length=255)
    cpf = models.CharField(
        max_length=14,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
                message='CPF deve estar no formato XXX.XXX.XXX-XX'
            )
        ]
    )
    
    # Controle de acesso
    role = models.CharField(max_length=10, choices=ROLES, default='USER')
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    
    # Segurança
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # MFA
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'cpf']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['cpf']),
        ]
    
    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        return self.is_admin
    
    def has_module_perms(self, app_label):
        return self.is_admin
    
    @property
    def is_staff(self):
        return self.is_admin
    
    def is_account_locked(self):
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def increment_failed_login(self):
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        if self.failed_login_attempts >= 5:
            # Bloquear por 30 minutos
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
        
        self.save()
    
    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save()

class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.CharField(max_length=500, unique=True, db_index=True)
    refresh_token = models.CharField(max_length=500, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sessions'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_active']),
        ]

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action']),
        ]

class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'password_reset_tokens'
    
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at
    
    @classmethod
    def create_for_user(cls, user):
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(hours=1)
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )