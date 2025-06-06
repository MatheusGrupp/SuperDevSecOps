FROM mysql:8.0

# copia o script sql
COPY db.sql /docker-entrypoint-initdb.d/

# Exponha a porta do MySQL
EXPOSE 3306