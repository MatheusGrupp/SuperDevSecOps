CREATE DATABASE IF NOT EXISTS projetosemestral;
USE projetosemestral;

CREATE TABLE IF NOT EXISTS usuario (
    email VARCHAR(200) NOT NULL,
    nome VARCHAR(200),
    cpf BIGINT,
    senha VARCHAR(200),
    PRIMARY KEY (email)
);

CREATE TABLE IF NOT EXISTS produto (
    nome VARCHAR(200) NOT NULL,
    descricao VARCHAR(1000),
    valor INT,
    PRIMARY KEY (nome)
);

CREATE TABLE IF NOT EXISTS carrinho (
    nome VARCHAR(200) NOT NULL,
    descricao VARCHAR(1000),
    valor INT,
    PRIMARY KEY (nome)
);

INSERT INTO produto (nome, descricao, valor)
VALUES 
    ('Bermuda Cyclone', 'BERMUDA AZUL PRA COMBINAR COM O KENNER', 379),
    ('Boné Kondzilla', 'BONÉ DE SUCESSO', 100),
    ('Camisa do Messi', '9 EM 10 NO BAILE TÃO USANDO, SÓ FALTA VOCÊ', 240),
    ('Chinelo Kenner', 'DE KENNER', 150),
    ('Corrente de Ouro', 'CORRENTE DE OURO 24K 70CM', 2990),
    ('Óculos Juliet', 'UM ITEM DE CRIA QUE NÃO PODE FALTAR', 125);

-- Cria o usuário e concede privilégios
CREATE USER IF NOT EXISTS 'toor'@'%' IDENTIFIED BY 'senhasecure1234#';
GRANT ALL PRIVILEGES ON projetosemestral.* TO 'toor'@'%';
FLUSH PRIVILEGES;

