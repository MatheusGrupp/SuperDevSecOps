#!/bin/bash

# Script de varredura de segredos no código
# Compatível com o pipeline DevSecOps

set -euo pipefail

echo "🔍 Iniciando varredura de segredos - SuperDevSecOps..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="${1:-.}"
REPORT_DIR="security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Criar diretório de relatórios
mkdir -p "$REPORT_DIR"

# Função para verificar instalação de ferramentas
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}❌ $1 não está instalado${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ $1 instalado${NC}"
    return 0
}

# Função para instalar ferramentas necessárias
install_tools() {
    echo -e "${BLUE}Instalando ferramentas de segurança...${NC}"
    
    # GitLeaks
    if ! command -v gitleaks &> /dev/null; then
        echo "Instalando GitLeaks..."
        wget -q https://github.com/zricethezav/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
        tar -xzf gitleaks_linux_amd64.tar.gz
        sudo mv gitleaks /usr/local/bin/
        rm gitleaks_linux_amd64.tar.gz
    fi
    
    # TruffleHog
    if ! command -v trufflehog &> /dev/null; then
        echo "Instalando TruffleHog..."
        pip install truffleHog3
    fi
}

# Verificar ferramentas necessárias
echo -e "${BLUE}Verificando ferramentas...${NC}"
TOOLS_OK=true

check_tool "git" || TOOLS_OK=false
check_tool "python3" || TOOLS_OK=false

if [ "$TOOLS_OK" = false ]; then
    echo -e "${RED}Por favor, instale as ferramentas básicas necessárias${NC}"
    exit 1
fi

# Instalar ferramentas de segurança se necessário
install_tools

# Executar GitLeaks
echo -e "\n${YELLOW}Executando GitLeaks...${NC}"
GITLEAKS_REPORT="$REPORT_DIR/gitleaks-report-$TIMESTAMP.json"

if gitleaks detect --source="$PROJECT_DIR" --report-format=json --report-path="$GITLEAKS_REPORT" --no-git; then
    echo -e "${GREEN}✅ GitLeaks: Nenhum segredo encontrado${NC}"
else
    echo -e "${RED}❌ GitLeaks: Segredos detectados! Verifique $GITLEAKS_REPORT${NC}"
    SECRETS_FOUND=true
fi

# Executar TruffleHog
echo -e "\n${YELLOW}Executando TruffleHog...${NC}"
TRUFFLEHOG_REPORT="$REPORT_DIR/trufflehog-report-$TIMESTAMP.json"

if python3 -m truffleHog3 -f json -o "$TRUFFLEHOG_REPORT" "$PROJECT_DIR" 2>/dev/null; then
    if [ ! -s "$TRUFFLEHOG_REPORT" ]; then
        echo -e "${GREEN}✅ TruffleHog: Nenhum segredo encontrado${NC}"
    else
        echo -e "${RED}❌ TruffleHog: Possíveis segredos detectados!${NC}"
        SECRETS_FOUND=true
    fi
fi

# Verificações personalizadas para Django
echo -e "\n${YELLOW}Executando verificações específicas do Django...${NC}"

# Padrões de segredos Django
DJANGO_PATTERNS=(
    "SECRET_KEY\s*=\s*['\"].*['\"]"
    "DATABASE_URL\s*=\s*['\"].*['\"]"
    "password\s*=\s*['\"].*['\"]"
    "POSTGRES_PASSWORD\s*=\s*['\"].*['\"]"
    "JWT_SECRET\s*=\s*['\"].*['\"]"
    "API_KEY\s*=\s*['\"].*['\"]"
    "AWS_SECRET_ACCESS_KEY"
    "STRIPE_SECRET_KEY"
)

CUSTOM_REPORT="$REPORT_DIR/custom-scan-$TIMESTAMP.txt"
FOUND_CUSTOM_SECRETS=false

for pattern in "${DJANGO_PATTERNS[@]}"; do
    echo -e "\nVerificando padrão: $pattern" >> "$CUSTOM_REPORT"
    if grep -r -i -E "$pattern" "$PROJECT_DIR" \
        --exclude-dir=.git \
        --exclude-dir=__pycache__ \
        --exclude-dir=venv \
        --exclude-dir=env \
        --exclude-dir=node_modules \
        --exclude-dir=staticfiles \
        --exclude-dir=media \
        --exclude-dir=security-reports \
        --exclude="*.pyc" \
        --exclude="*.log" \
        --exclude="*.sqlite3" \
        --exclude="*-report.*" \
        --exclude=".env.example" \
        >> "$CUSTOM_REPORT" 2>/dev/null; then
        echo -e "${RED}❌ Padrão suspeito encontrado: $pattern${NC}"
        FOUND_CUSTOM_SECRETS=true
    fi
done

if [ "$FOUND_CUSTOM_SECRETS" = false ]; then
    echo -e "${GREEN}✅ Verificações personalizadas: OK${NC}"
fi

# Verificar arquivos .env
echo -e "\n${YELLOW}Verificando arquivos de ambiente...${NC}"
ENV_FILES=$(find "$PROJECT_DIR" -name ".env" -o -name ".env.*" | grep -v ".env.example" || true)

if [ -n "$ENV_FILES" ]; then
    echo -e "${RED}❌ Arquivos .env encontrados no repositório!${NC}"
    echo "$ENV_FILES"
    echo -e "\n${YELLOW}Arquivos .env encontrados:${NC}" >> "$CUSTOM_REPORT"
    echo "$ENV_FILES" >> "$CUSTOM_REPORT"
    SECRETS_FOUND=true
else
    echo -e "${GREEN}✅ Nenhum arquivo .env comprometedor encontrado${NC}"
fi

# Verificar arquivos de configuração sensíveis
echo -e "\n${YELLOW}Verificando arquivos de configuração...${NC}"
SENSITIVE_FILES=(
    "*.pem"
    "*.key"
    "*.p12"
    "*.pfx"
    "id_rsa"
    "id_dsa"
    "*.ppk"
)

for pattern in "${SENSITIVE_FILES[@]}"; do
    FOUND_FILES=$(find "$PROJECT_DIR" -name "$pattern" 2>/dev/null || true)
    if [ -n "$FOUND_FILES" ]; then
        echo -e "${RED}❌ Arquivos sensíveis encontrados: $pattern${NC}"
        echo -e "\nArquivos sensíveis ($pattern):" >> "$CUSTOM_REPORT"
        echo "$FOUND_FILES" >> "$CUSTOM_REPORT"
        SECRETS_FOUND=true
    fi
done

# Gerar relatório consolidado
echo -e "\n${BLUE}Gerando relatório consolidado...${NC}"
CONSOLIDATED_REPORT="$REPORT_DIR/security-scan-summary-$TIMESTAMP.md"

cat > "$CONSOLIDATED_REPORT" << EOF
# Relatório de Varredura de Segurança - SuperDevSecOps

**Data:** $(date)
**Diretório:** $PROJECT_DIR

## Resumo Executivo

EOF

if [ "${SECRETS_FOUND:-false}" = true ]; then
    cat >> "$CONSOLIDATED_REPORT" << EOF
⚠️ **ATENÇÃO: Possíveis segredos ou arquivos sensíveis foram detectados!**

Por favor, revise os relatórios detalhados e tome as seguintes ações:
1. Remova imediatamente qualquer segredo do código
2. Rotacione todas as credenciais expostas
3. Use variáveis de ambiente para configurações sensíveis
4. Adicione arquivos sensíveis ao .gitignore

EOF
else
    cat >> "$CONSOLIDATED_REPORT" << EOF
✅ **Nenhum segredo ou arquivo sensível foi detectado.**

Continue seguindo as boas práticas de segurança:
- Sempre use variáveis de ambiente para segredos
- Nunca commite arquivos .env
- Mantenha o .gitignore atualizado
- Execute esta verificação regularmente

EOF
fi

cat >> "$CONSOLIDATED_REPORT" << EOF

## Ferramentas Utilizadas

- **GitLeaks:** Detecção de segredos em repositórios Git
- **TruffleHog:** Busca por strings de alta entropia
- **Verificações Customizadas:** Padrões específicos do Django

## Relatórios Detalhados

- GitLeaks: $GITLEAKS_REPORT
- TruffleHog: $TRUFFLEHOG_REPORT
- Verificações Customizadas: $CUSTOM_REPORT

## Recomendações de Segurança

1. **Gerenciamento de Segredos:**
   - Use ferramentas como HashiCorp Vault ou AWS Secrets Manager
   - Implemente rotação automática de credenciais
   - Use tokens com escopo limitado e prazo de validade

2. **Controle de Versão:**
   - Configure pre-commit hooks para prevenir commits de segredos
   - Use .gitignore abrangente
   - Revise o histórico do Git regularmente

3. **CI/CD Pipeline:**
   - Integre esta verificação no pipeline
   - Falhe o build se segredos forem detectados
   - Notifique a equipe de segurança automaticamente

4. **Treinamento:**
   - Eduque desenvolvedores sobre segurança de código
   - Estabeleça políticas claras de gerenciamento de segredos
   - Realize auditorias regulares

---

*Relatório gerado automaticamente pelo sistema de segurança SuperDevSecOps*
EOF

echo -e "\n${GREEN}✅ Varredura de segurança concluída!${NC}"
echo -e "${BLUE}Relatório consolidado salvo em: $CONSOLIDATED_REPORT${NC}"

# Retornar código de erro se segredos foram encontrados
if [ "${SECRETS_FOUND:-false}" = true ]; then
    exit 1
fi

exit 0