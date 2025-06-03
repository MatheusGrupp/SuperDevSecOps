#!/bin/bash

# Script de setup para SuperDevSecOps
# Compatível com a documentação do projeto

set -e

echo "🚀 Iniciando setup do SuperDevSecOps..."

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar Docker
echo -e "${BLUE}Verificando Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker não encontrado. Por favor, instale o Docker primeiro.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose não encontrado. Por favor, instale o Docker Compose primeiro.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker e Docker Compose instalados${NC}"

# Criar estrutura de diretórios
echo -e "${BLUE}Criando estrutura de diretórios...${NC}"

directories=(
    "api-gateway/gateway"
    "api-gateway/core"
    "auth-service/auth_service"
    "auth-service/authentication"
    "task-service/task_service"
    "task-service/tasks"
    "monitoring"
    "security/scripts"
    "databases/auth-db"
    "databases/task-db"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    touch "$dir/__init__.py"
done

echo -e "${GREEN}✓ Estrutura de diretórios criada${NC}"

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo -e "${BLUE}Criando arquivo .env...${NC}"
    cp .env.example .env
    
    # Gerar secrets aleatórios
    GATEWAY_SECRET=$(openssl rand -base64 32)
    AUTH_SECRET=$(openssl rand -base64 32)
    TASK_SECRET=$(openssl rand -base64 32)
    JWT_SECRET=$(openssl rand -base64 32)
    DB_PASSWORD=$(openssl rand -base64 16)
    REDIS_PASSWORD=$(openssl rand -base64 16)
    GRAFANA_PASSWORD=$(openssl rand -base64 16)
    
    # Substituir no .env
    sed -i "s/your-gateway-secret-key-here/$GATEWAY_SECRET/g" .env
    sed -i "s/your-auth-secret-key-here/$AUTH_SECRET/g" .env
    sed -i "s/your-task-secret-key-here/$TASK_SECRET/g" .env
    sed -i "s/your-jwt-secret-key-here/$JWT_SECRET/g" .env
    sed -i "s/your-secure-database-password/$DB_PASSWORD/g" .env
    sed -i "s/your-redis-password/$REDIS_PASSWORD/g" .env
    sed -i "s/your-grafana-password/$GRAFANA_PASSWORD/g" .env
    
    echo -e "${GREEN}✓ Arquivo .env criado com secrets seguros${NC}"
fi

# Criar Dockerfiles
echo -e "${BLUE}Criando Dockerfiles...${NC}"

# Dockerfile para Django services
cat > api-gateway/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar usuário não-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expor porta
EXPOSE 8000

# Comando
CMD ["gunicorn", "gateway.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
EOF

cp api-gateway/Dockerfile auth-service/Dockerfile
cp api-gateway/Dockerfile task-service/Dockerfile

# Ajustar portas nos Dockerfiles
sed -i 's/8000/8001/g' auth-service/Dockerfile
sed -i 's/gateway/auth_service/g' auth-service/Dockerfile

sed -i 's/8000/8002/g' task-service/Dockerfile
sed -i 's/gateway/task_service/g' task-service/Dockerfile

echo -e "${GREEN}✓ Dockerfiles criados${NC}"

# Criar manage.py files
echo -e "${BLUE}Criando arquivos manage.py...${NC}"

for service in api-gateway auth-service task-service; do
    module_name=$(echo $service | sed 's/-/_/g')
    cat > "$service/manage.py" << EOF
#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${module_name}.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
EOF
    chmod +x "$service/manage.py"
done

echo -e "${GREEN}✓ Arquivos manage.py criados${NC}"

# Criar arquivo nginx.conf
cat > nginx.conf << 'EOF'
user nginx;
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://api-gateway:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
EOF

echo -e "${GREEN}✓ nginx.conf criado${NC}"

# Criar arquivo security.txt
cat > frontend/security.txt << 'EOF'
Contact: security@superdevsecops.com
Expires: 2025-12-31T23:59:59.000Z
Acknowledgments: https://superdevsecops.com/security/hall-of-fame
Preferred-Languages: pt, en
Canonical: https://superdevsecops.com/.well-known/security.txt
Policy: https://superdevsecops.com/security/policy
Hiring: https://superdevsecops.com/careers
EOF

echo -e "${GREEN}✓ security.txt criado${NC}"

# Criar prometheus.yml
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
  
  - job_name: 'auth-service'
    static_configs:
      - targets: ['auth-service:8001']
  
  - job_name: 'task-service'
    static_configs:
      - targets: ['task-service:8002']
EOF

echo -e "${GREEN}✓ prometheus.yml criado${NC}"

# Build das imagens
echo -e "${YELLOW}Construindo imagens Docker...${NC}"
docker-compose build

echo -e "${GREEN}✓ Imagens construídas${NC}"

# Iniciar serviços
echo -e "${YELLOW}Iniciando serviços...${NC}"
docker-compose up -d

# Aguardar serviços iniciarem
echo -e "${BLUE}Aguardando serviços iniciarem...${NC}"
sleep 30

# Executar migrações
echo -e "${BLUE}Executando migrações do banco de dados...${NC}"

docker-compose exec -T api-gateway python manage.py migrate
docker-compose exec -T auth-service python manage.py migrate
docker-compose exec -T task-service python manage.py migrate

echo -e "${GREEN}✓ Migrações executadas${NC}"

# Criar superusuário
echo -e "${BLUE}Criando usuário administrador...${NC}"

docker-compose exec -T auth-service python manage.py shell << 'EOF'
from authentication.models import User
if not User.objects.filter(email='admin@superdevsecops.com').exists():
    User.objects.create_superuser(
        email='admin@superdevsecops.com',
        nome='Administrador',
        cpf='111.111.111-11',
        password='Admin@123'
    )
    print("Usuário admin criado com sucesso!")
else:
    print("Usuário admin já existe!")
EOF

echo -e "${GREEN}✓ Setup concluído com sucesso!${NC}"

echo -e "\n${BLUE}URLs de acesso:${NC}"
echo -e "Frontend: ${GREEN}http://localhost${NC}"
echo -e "API Gateway: ${GREEN}http://localhost:8000${NC}"
echo -e "Prometheus: ${GREEN}http://localhost:9090${NC}"
echo -e "Grafana: ${GREEN}http://localhost:3000${NC} (admin / password do .env)"

echo -e "\n${BLUE}Credenciais padrão:${NC}"
echo -e "Admin: ${GREEN}admin@superdevsecops.com / Admin@123${NC}"

echo -e "\n${YELLOW}⚠️  IMPORTANTE:${NC}"
echo -e "1. Altere a senha do admin após o primeiro login"
echo -e "2. Revise e ajuste as configurações no arquivo .env"
echo -e "3. Configure certificados SSL para produção"
echo -e "4. Ative o backup automático dos bancos de dados"

echo -e "\n${GREEN}🎉 SuperDevSecOps está pronto para uso!${NC}"