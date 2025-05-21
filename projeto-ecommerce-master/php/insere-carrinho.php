<?php

$nome = $_POST['nome'];

include "conexao.php";

// Preparar a consulta SQL para prevenir SQL Injection
$sql = "INSERT INTO carrinho SELECT * FROM produto WHERE nome = ?";

// Preparar o statement
$stmt = mysqli_prepare($con, $sql);

// Vincular o parâmetro
mysqli_stmt_bind_param($stmt, "s", $nome);

// Executar o statement
mysqli_stmt_execute($stmt);

// Fechar o statement
mysqli_stmt_close($stmt);

// Fechar a conexão
mysqli_close($con);
