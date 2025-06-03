from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'cpf', 'role', 'is_active', 
                 'mfa_enabled', 'created_at', 'last_login']
        read_only_fields = ['id', 'created_at', 'last_login']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Mascarar CPF
        if 'cpf' in data:
            cpf = data['cpf']
            data['cpf'] = f"{cpf[:3]}.***.**-{cpf[-2:]}"
        return data

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nome = serializers.CharField(max_length=255)
    cpf = serializers.RegexField(
        regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
        error_messages={
            'invalid': 'CPF deve estar no formato XXX.XXX.XXX-XX'
        }
    )
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email já cadastrado")
        return value
    
    def validate_cpf(self, value):
        if User.objects.filter(cpf=value).exists():
            raise serializers.ValidationError("CPF já cadastrado")
        
        # Validar CPF
        cpf = value.replace('.', '').replace('-', '')
        if len(cpf) != 11:
            raise serializers.ValidationError("CPF inválido")
        
        # Validação matemática do CPF
        def calculate_digit(cpf, digit):
            sum_digit = 0
            for index in range(digit):
                sum_digit += int(cpf[index]) * ((digit + 1) - index)
            remainder = sum_digit % 11
            return 0 if remainder < 2 else 11 - remainder
        
        first_digit = calculate_digit(cpf, 9)
        second_digit = calculate_digit(cpf, 10)
        
        if cpf[-2:] != f"{first_digit}{second_digit}":
            raise serializers.ValidationError("CPF inválido")
        
        return value
    
    def validate_password(self, value):
        # Validar complexidade da senha
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("A senha deve conter pelo menos um número")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("A senha deve conter pelo menos uma letra")
        return value