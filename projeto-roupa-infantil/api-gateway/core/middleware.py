import time
import logging
import json
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
import hashlib

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Adiciona headers de segurança em todas as respostas"""
    
    def process_response(self, request, response):
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # CSP
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.superdevsecops.com; "
            "frame-ancestors 'none';"
        )
        response['Content-Security-Policy'] = csp
        
        return response

class RateLimitMiddleware(MiddlewareMixin):
    """Implementa rate limiting para proteção contra DDoS"""
    
    def process_request(self, request):
        if not settings.RATELIMIT_ENABLE:
            return None
            
        # Obter IP do cliente
        ip = self.get_client_ip(request)
        
        # Criar chave única para o rate limit
        key = f"ratelimit:{ip}:{request.path}"
        
        # Verificar limite
        current_minute = int(time.time() / 60)
        minute_key = f"{key}:{current_minute}"
        
        try:
            current_count = cache.get(minute_key, 0)
            if current_count >= 100:  # 100 requisições por minuto
                logger.warning(f"Rate limit exceeded for IP {ip} on path {request.path}")
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.'
                }, status=429)
            
            # Incrementar contador
            cache.set(minute_key, current_count + 1, 60)
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Em caso de erro, permite a requisição
            
        return None
    
    def get_client_ip(self, request):
        """Obtém o IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class LoggingMiddleware(MiddlewareMixin):
    """Registra todas as requisições para auditoria"""
    
    def process_request(self, request):
        request.start_time = time.time()
        
        # Log da requisição
        logger.info(f"Request: {request.method} {request.path} from {self.get_client_ip(request)}")
        
        return None
    
    def process_response(self, request, response):
        # Calcular tempo de resposta
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
            
            # Log da resposta
            logger.info(
                f"Response: {request.method} {request.path} "
                f"Status: {response.status_code} "
                f"Duration: {duration:.3f}s"
            )
            
            # Alertar se resposta demorada
            if duration > 2.0:
                logger.warning(
                    f"Slow response: {request.method} {request.path} "
                    f"took {duration:.3f}s"
                )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class AuthenticationMiddleware(MiddlewareMixin):
    """Verifica autenticação JWT em rotas protegidas"""
    
    PUBLIC_PATHS = [
        '/api/auth/login',
        '/api/auth/register',
        '/api/auth/forgot-password',
        '/api/health',
        '/metrics',
        '/admin/',
    ]
    
    def process_request(self, request):
        # Pular autenticação para rotas públicas
        if any(request.path.startswith(path) for path in self.PUBLIC_PATHS):
            return None
        
        # Verificar token JWT
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Please provide a valid authentication token'
            }, status=401)
        
        # Token será validado no gateway
        return None

class CorrelationIdMiddleware(MiddlewareMixin):
    """Adiciona ID de correlação para rastreamento de requisições"""
    
    def process_request(self, request):
        # Gerar ou obter correlation ID
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID')
        if not correlation_id:
            # Gerar ID único baseado em timestamp e IP
            timestamp = str(time.time())
            ip = self.get_client_ip(request)
            correlation_id = hashlib.sha256(f"{timestamp}{ip}".encode()).hexdigest()[:16]
        
        request.correlation_id = correlation_id
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip