import os
import hvac
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Configurações do Vault
    vault_addr = os.environ.get('VAULT_ADDR')
    vault_token = os.environ.get('VAULT_TOKEN')
    secret_path = os.environ.get('VAULT_SECRET_PATH_DB_PASS')  # Exemplo: 'secret/data/cart'

    client = hvac.Client(url=vault_addr, token=vault_token)
    secret = client.secrets.kv.v2.read_secret_version(path=secret_path)
    db_password = secret['data']['data']['password']

    # Configuração do banco de dados
    db_user = 'cart_user'
    db_host = 'db'
    db_name = 'cart_db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Registro das rotas
    from .routes import cart_bp
    app.register_blueprint(cart_bp)

    return app
