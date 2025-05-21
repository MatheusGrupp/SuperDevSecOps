FROM php:8.1-apache

# Atualiza o repositório e instala a extensão mysqli
RUN apt-get update && \
    docker-php-ext-install mysqli && \
    docker-php-ext-enable mysqli

# Copia o código da aplicação para o diretório padrão do Apache
COPY . /var/www/html/

# Ajusta permissões para o Apache
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

# Exibe extensões PHP instaladas para depuração
RUN php -m

# Expõe a porta 80 para o Apache
EXPOSE 80

# Inicia o Apache em modo foreground
CMD ["apache2-foreground"]

