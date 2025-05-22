from app import app, db

if __name__ == "__main__":
    # Garante que as tabelas do banco de dados sejam criadas
    with app.app_context():
        db.create_all()
    # Executa a aplicação Flask na porta 5001, acessível externamente
    app.run(host="0.0.0.0", port=5001)
