from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import pyotp
import qrcode
import io
import base64
import logging
from .models import User, UserRole
from .serializers import UserSerializer, LoginSerializer
from mfa.models import MFADevice

logger = logging.getLogger(__name__)

@api_view(['POST'])
def login(request):
    """Authenticate user with optional MFA"""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    mfa_token = serializer.validated_data.get('mfa_token')
    
    try:
        user = User.objects.get(email=email)
        
        # Check if account is locked
        if user.locked_until and user.locked_until > timezone.now():
            logger.warning(f"Login attempt for locked account: {email}")
            return Response({'error': 'Account temporarily locked'}, status=status.HTTP_423_LOCKED)
        
        # Authenticate user
        if not user.check_password(password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = timezone.now() + timedelta(minutes=30)
            user.save()
            logger.warning(f"Failed login attempt for user: {email}")
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check MFA if enabled
        if user.is_mfa_enabled:
            if not mfa_token:
                return Response({'mfa_required': True}, status=status.HTTP_200_OK)
            
            mfa_device = MFADevice.objects.get(user=user, is_active=True)
            totp = pyotp.TOTP(mfa_device.secret)
            if not totp.verify(mfa_token, valid_window=1):
                logger.warning(f"Invalid MFA token for user: {email}")
                return Response({'error': 'Invalid MFA token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add user roles to token
        roles = list(UserRole.objects.filter(user=user).values_list('role__name', flat=True))
        access_token['roles'] = roles
        
        logger.info(f"Successful login for user: {email}")
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        logger.warning(f"Login attempt for non-existent user: {email}")
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def register(request):
    """Register new user"""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        logger.info(f"New user registered: {user.email}")
        return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_mfa(request):
    """Enable MFA for user"""
    user = request.user
    
    if user.is_mfa_enabled:
        return Response({'error': 'MFA already enabled'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate TOTP secret
    secret = pyotp.random_base32()
    
    # Create MFA device
    mfa_device = MFADevice.objects.create(
        user=user,
        secret=secret,
        device_type='totp',
        is_active=False
    )
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="SuperDevSecOps"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_code_data = base64.b64encode(buffer.read()).decode()
    
    return Response({
        'secret': secret,
        'qr_code': f"data:image/png;base64,{qr_code_data}",
        'device_id': mfa_device.id
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_mfa(request):
    """Verify MFA setup"""
    device_id = request.data.get('device_id')
    token = request.data.get('token')
    
    try:
        mfa_device = MFADevice.objects.get(id=device_id, user=request.user, is_active=False)
        totp = pyotp.TOTP(mfa_device.secret)
        
        if totp.verify(token, valid_window=1):
            mfa_device.is_active = True
            mfa_device.save()
            
            request.user.is_mfa_enabled = True
            request.user.save()
            
            logger.info(f"MFA enabled for user: {request.user.email}")
            return Response({'message': 'MFA enabled successfully'})
        else:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
            
    except MFADevice.DoesNotExist:
        return Response({'error': 'Invalid device'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get user profile"""
    return Response(UserSerializer(request.user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user"""
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info(f"User logged out: {request.user.email}")
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)