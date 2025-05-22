from flask import request, jsonify, render_template
from app import app, db, JWT_SECRET
from app.models import Product
import jwt
from functools import wraps

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Obtém token JWT do Authorization header ou cookie
            token = None
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1]
            if not token:
                token = request.cookies.get('token')
            if not token:
                # Sem token -> não autorizado
                return "Unauthorized", 401
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            except Exception:
                return "Invalid token", 401
            if role and payload.get('role') != role:
                return "Forbidden", 403
            # Anexa payload para uso na função
            request.user_payload = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/', methods=['GET'])
def list_products_page():
    # Se usuário logado, decodifica para saudação/admin link
    token = request.cookies.get('token')
    username = None
    is_admin = False
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            username = payload.get('username')
            if payload.get('role') == 'admin':
                is_admin = True
        except Exception:
            pass
    products = Product.query.all()
    return render_template('product_list.html', products=products, username=username, is_admin=is_admin)

@app.route('/api/products', methods=['GET'])
def api_list_products():
    products = Product.query.all()
    data = [{"id": p.id, "name": p.name, "price": p.price} for p in products]
    return jsonify(data)

@app.route('/api/product/<int:pid>', methods=['GET'])
def api_get_product(pid):
    product = Product.query.get(pid)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    data = {"id": product.id, "name": product.name, "price": product.price}
    return jsonify(data)

@app.route('/api/products', methods=['POST'])
@login_required(role='admin')
def api_add_product():
    data = request.get_json()
    if not data or 'name' not in data or 'price' not in data:
        return jsonify({"error": "Name and price required"}), 400
    name = data['name']
    price = data['price']
    if not name or price is None:
        return jsonify({"error": "Invalid product data"}), 400
    product = Product(name=name, price=float(price))
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product created", "id": product.id}), 201

@app.route('/api/product/<int:pid>', methods=['DELETE'])
@login_required(role='admin')
def api_delete_product(pid):
    product = Product.query.get(pid)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})
