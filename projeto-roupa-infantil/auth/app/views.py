from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import jwt
import pyotp
from datetime import datetime, timedelta
from .models import User, Session, AuditLog, PasswordResetToken
from .serializers import UserSerializer, LoginSerializer, RegisterSerializer

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')

def create_audit_log(user, action, details, request):
    AuditLog.objects.create(
        user=user,
        action=action,
        details=details,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

def generate_tokens(user):
    # Access token (15 minutos)
    access_payload = {
        'user_id': str(user.id),
        'email': user.email,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(minutes=15),
        'iat': datetime.utcnow()
    }
    access_token = jwt.encode(access_payload, settings.JWT_SECRET, algorithm='HS256')
    
    # Refresh token (7 dias)
    refresh_payload = {
        'user_id': str(user.id),
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET, algorithm='HS256')
    
    return access_token, refresh_token

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    try:
        user = User.objects.get(email=email)
        
        # Verificar se a conta está bloqueada
        if user.is_account_locked():
            return Response({
                'error': 'Conta bloqueada devido a múltiplas tentativas de login falhadas. Tente novamente mais tarde.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Autenticar
        if not user.check_password(password):
            user.increment_failed_login()
            create_audit_log(None, 'LOGIN_FAILED', {'email': email}, request)
            return Response({
                'error': 'Credenciais inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Reset tentativas falhadas
        user.reset_failed_attempts()
        user.last_login = timezone.now()
        user.save()
        
        # Verificar MFA
        if user.mfa_enabled:
            # Gerar token temporário para MFA
            mfa_token = jwt.encode({
                'user_id': str(user.id),
                'type': 'mfa',
                'exp': datetime.utcnow() + timedelta(minutes=5)
            }, settings.JWT_SECRET, algorithm='HS256')
            
            return Response({
                'requires_mfa': True,
                'mfa_token': mfa_token
            })
        
        # Gerar tokens
        access_token, refresh_token = generate_tokens(user)
        
        # Criar sessão
        Session.objects.create(
            user=user,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Audit log
        create_audit_log(user, 'LOGIN_SUCCESS', {}, request)
        
        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        # Não revelar se o usuário existe
        return Response({
            'error': 'Credenciais inválidas'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar se as senhas conferem
    if serializer.validated_data['password'] != serializer.validated_data.get('password_confirm'):
        return Response({
            'error': 'As senhas não conferem'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Criar usuário
    user = User.objects.create_user(
        email=serializer.validated_data['email'],
        nome=serializer.validated_data['nome'],
        cpf=serializer.validated_data['cpf'],
        password=serializer.validated_data['password']
    )
    
    # Audit log
    create_audit_log(user, 'USER_REGISTERED', {}, request)
    
    # Enviar email de boas-vindas
    send_mail(
        'Bem-vindo ao SuperDevSecOps',
        f'Olá {user.nome},\n\nSua conta foi criada com sucesso!',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )
    
    return Response({
        'success': True,
        'message': 'Usuário criado com sucesso',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    # Obter token do header
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    
    # Invalidar sessão
    try:
        session = Session.objects.get(token=token, user=request.user)
        session.is_active = False
        session.save()
    except Session.DoesNotExist:
        pass
    
    # Audit log
    create_audit_log(request.user, 'LOGOUT', {}, request)
    
    return Response({'success': True})

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'error': 'Refresh token não fornecido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Decodificar refresh token
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=['HS256'])
        
        if payload.get('type') != 'refresh':
            raise jwt.InvalidTokenError
        
        # Buscar usuário
        user = User.objects.get(id=payload['user_id'])
        
        # Verificar se a sessão ainda é válida
        session = Session.objects.get(refresh_token=refresh_token, user=user, is_active=True)
        
        # Gerar novos tokens
        access_token, new_refresh_token = generate_tokens(user)
        
        # Atualizar sessão
        session.token = access_token
        session.refresh_token = new_refresh_token
        session.save()
        
        return Response({
            'access_token': access_token,
            'refresh_token': new_refresh_token
        })
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist, Session.DoesNotExist):
        return Response({
            'error': 'Refresh token inválido ou expirado'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email é obrigatório'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        
        # Criar token de reset
        reset_token = PasswordResetToken.create_for_user(user)
        
        # Enviar email
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token.token}"
        send_mail(
            'Recuperação de Senha - SuperDevSecOps',
            f'Olá {user.nome},\n\nClique no link abaixo para redefinir sua senha:\n{reset_link}\n\nEste link é válido por 1 hora.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        # Audit log
        create_audit_log(user, 'PASSWORD_RESET_REQUESTED', {}, request)
        
    except User.DoesNotExist:
        # Não revelar se o email existe
        pass
    
    return Response({
        'success': True,
        'message': 'Se o email existir em nossa base, você receberá instruções de recuperação.'
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    
    if not token or not new_password:
        return Response({
            'error': 'Token e nova senha são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        
        if not reset_token.is_valid():
            return Response({
                'error': 'Token inválido ou expirado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Redefinir senha
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Marcar token como usado
        reset_token.used = True
        reset_token.save()
        
        # Invalidar todas as sessões do usuário
        Session.objects.filter(user=user).update(is_active=False)
        
        # Audit log
        create_audit_log(user, 'PASSWORD_RESET_COMPLETED', {}, request)
        
        # Enviar email de confirmação
        send_mail(
            'Senha Alterada - SuperDevSecOps',
            f'Olá {user.nome},\n\nSua senha foi alterada com sucesso. Se você não fez esta alteração, entre em contato imediatamente.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True
        )
        
        return Response({
            'success': True,
            'message': 'Senha alterada com sucesso'
        })
        
    except PasswordResetToken.DoesNotExist:
        return Response({
            'error': 'Token inválido'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_mfa(request):
    mfa_token = request.data.get('mfa_token')
    code = request.data.get('code')
    
    if not mfa_token or not code:
        return Response({
            'error': 'Token MFA e código são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Decodificar token MFA
        payload = jwt.decode(mfa_token, settings.JWT_SECRET, algorithms=['HS256'])
        
        if payload.get('type') != 'mfa':
            raise jwt.InvalidTokenError
        
        # Buscar usuário
        user = User.objects.get(id=payload['user_id'])
        
        # Verificar código TOTP
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            return Response({
                'error': 'Código MFA inválido'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Gerar tokens de acesso
        access_token, refresh_token = generate_tokens(user)
        
        # Criar sessão
        Session.objects.create(
            user=user,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Audit log
        create_audit_log(user, 'MFA_VERIFIED', {}, request)
        
        return Response({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': UserSerializer(user).data
        })
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return Response({
            'error': 'Token MFA inválido ou expirado'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    return Response(UserSerializer(user).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    
    # Campos permitidos para atualização
    allowed_fields = ['nome', 'email']
    
    for field in allowed_fields:
        if field in request.data:
            setattr(user, field, request.data[field])
    
    user.save()
    
    # Audit log
    create_audit_log(user, 'PROFILE_UPDATED', request.data, request)
    
    return Response(UserSerializer(user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response({
            'error': 'Senha atual e nova senha são obrigatórias'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar senha atual
    if not user.check_password(current_password):
        return Response({
            'error': 'Senha atual incorreta'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Alterar senha
    user.set_password(new_password)
    user.save()
    
    # Invalidar todas as sessões
    Session.objects.filter(user=user).update(is_active=False)
    
    # Audit log
    create_audit_log(user, 'PASSWORD_CHANGED', {}, request)
    
    # Enviar email
    send_mail(
        'Senha Alterada - SuperDevSecOps',
        f'Olá {user.nome},\n\nSua senha foi alterada com sucesso. Se você não fez esta alteração, entre em contato imediatamente.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )
    
    return Response({
        'success': True,
        'message': 'Senha alterada com sucesso. Por favor, faça login novamente.'
    })

# Admin endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    # Verificar se é admin
    if request.user.role != 'ADMIN':
        return Response({
            'error': 'Acesso negado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    users = User.objects.all()
    return Response(UserSerializer(users, many=True).data)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    # Verificar se é admin
    if request.user.role != 'ADMIN':
        return Response({
            'error': 'Acesso negado'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'Usuário não encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        return Response(UserSerializer(user).data)
    
    elif request.method == 'PUT':
        # Atualizar usuário
        allowed_fields = ['nome', 'email', 'role', 'is_active']
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        
        # Audit log
        create_audit_log(request.user, 'USER_UPDATED_BY_ADMIN', {
            'target_user': str(user.id),
            'changes': request.data
        }, request)
        
        return Response(UserSerializer(user).data)
    
    elif request.method == 'DELETE':
        # Soft delete - apenas desativar
        user.is_active = False
        user.save()
        
        # Invalidar sessões
        Session.objects.filter(user=user).update(is_active=False)
        
        # Audit log
        create_audit_log(request.user, 'USER_DELETED_BY_ADMIN', {
            'target_user': str(user.id)
        }, request)
        
        return Response(status=status.HTTP_204_NO_CONTENT)