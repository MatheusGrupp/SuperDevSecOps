from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os, requests

app = Flask(__name__)

# Configurações de banco de dados e Vault
DB_HOST = os.environ.get('DB_HOST', 'auth-db')
DB_NAME = os.environ.get('DB_NAME', 'auth_db')
DB_USER = os.environ.get('DB_USER', 'auth_user')
DB_PASSWORD = None
JWT_SECRET = None

vault_addr = os.environ.get('VAULT_ADDR')
vault_token = os.environ.get('VAULT_TOKEN')
# Busca segredos no Vault, se configurado
if vault_addr and vault_token:
    try:
        # Busca a chave JWT secreta no Vault (KV store)
        url = f"{vault_addr}/v1/secret/data/jwt_secret"
        res = requests.get(url, headers={"X-Vault-Token": vault_token})
        if res.status_code == 200:
            JWT_SECRET = res.json()['data']['data']['value']
        # Busca a senha do DB de Auth no Vault
        secret_key = os.environ.get('VAULT_SECRET_KEY_DB_PASS')
        if secret_key:
            url = f"{vault_addr}/v1/secret/data/{secret_key}"
            res2 = requests.get(url, headers={"X-Vault-Token": vault_token})
            if res2.status_code == 200:
                DB_PASSWORD = res2.json()['data']['data']['value']
    except Exception as e:
        print("Vault secrets retrieval failed:", e)

# Fallback para desenvolvimento, se Vault não disponível
if not JWT_SECRET:
    JWT_SECRET = os.environ.get('JWT_SECRET', 'DEVSECRET')
if not DB_PASSWORD:
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

# Configuração da URI de conexão PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Importa módulos para registrar modelos e rotas
from app import models, views
