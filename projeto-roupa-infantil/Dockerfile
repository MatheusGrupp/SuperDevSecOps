# Dockerfile
FROM php:8.2-apache

# Instalar extensões PHP necessárias
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libzip-dev \
    unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) \
    gd \
    mysqli \
    pdo \
    pdo_mysql \
    zip \
    opcache

# Habilitar mod_rewrite do Apache
RUN a2enmod rewrite headers

# Configurar Apache
RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Configuração personalizada do Apache
COPY <<EOF /etc/apache2/sites-available/000-default.conf
<VirtualHost *:80>
    DocumentRoot /var/www/html
    
    <Directory /var/www/html>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    
    ErrorLog \${APACHE_LOG_DIR}/error.log
    CustomLog \${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
EOF

# Configurar PHP
RUN echo "memory_limit = 256M" > /usr/local/etc/php/conf.d/memory.ini && \
    echo "upload_max_filesize = 64M" >> /usr/local/etc/php/conf.d/memory.ini && \
    echo "post_max_size = 64M" >> /usr/local/etc/php/conf.d/memory.ini

# Copiar arquivos da aplicação
COPY . /var/www/html/

# Dar permissões corretas
RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html

# Criar diretório de uploads se não existir
RUN mkdir -p /var/www/html/uploads && \
    chown -R www-data:www-data /var/www/html/uploads

EXPOSE 80

CMD ["apache2-foreground"]