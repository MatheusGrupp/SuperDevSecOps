from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
import requests
import jwt
from functools import wraps
import logging
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, origins=['http://localhost:3000', 'https://localhost'])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.Integer, default=1)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Auth decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            user_roles = data.get('roles', [])
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user_id, user_roles, *args, **kwargs)
    
    return decorated

# Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'task-service'}), 200

@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user_id, user_roles):
    """Get all tasks for the current user"""
    try:
        tasks = Task.query.filter_by(user_id=current_user_id).all()
        return jsonify([task.to_dict() for task in tasks]), 200
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks', methods=['POST'])
@token_required
def create_task(current_user_id, user_roles):
    """Create a new task"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            user_id=current_user_id,
            status=data.get('status', 'pending'),
            priority=data.get('priority', 1),
            due_date=datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')) if data.get('due_date') else None
        )
        
        db.session.add(task)
        db.session.commit()
        
        logger.info(f"Task created: {task.id} by user: {current_user_id}")
        return jsonify(task.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
@token_required
def get_task(current_user_id, user_roles, task_id):
    """Get a specific task"""
    try:
        task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task.to_dict()), 200
    except Exception as e:
        logger.error(f"Error fetching task: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks/<task_id>', methods=['PUT'])
@token_required
def update_task(current_user_id, user_roles, task_id):
    """Update a specific task"""
    try:
        task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'status' in data:
            task.status = data['status']
        if 'priority' in data:
            task.priority = data['priority']
        if 'due_date' in data:
            task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')) if data['due_date'] else None
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Task updated: {task.id} by user: {current_user_id}")
        return jsonify(task.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user_id, user_roles, task_id):
    """Delete a specific task"""
    try:
        task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        db.session.delete(task)
        db.session.commit()
        
        logger.info(f"Task deleted: {task.id} by user: {current_user_id}")
        return jsonify({'message': 'Task deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)