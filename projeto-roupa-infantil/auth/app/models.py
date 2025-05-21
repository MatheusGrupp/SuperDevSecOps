from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    
    def set_password(self, password):
        """Gera hash e armazena a senha."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica a senha em texto plano contra o hash armazenado."""
        return check_password_hash(self.password_hash, password)
