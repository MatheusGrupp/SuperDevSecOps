<?php
if (isset($_POST['nome']) && isset($_POST['cpf']) && isset($_POST['email']) && isset($_POST['password'])) {
    include "conexao.php";

    $nome = mysqli_real_escape_string($con, $_POST['nome']);
    $cpf = mysqli_real_escape_string($con, $_POST['cpf']);
    $email = mysqli_real_escape_string($con, $_POST['email']);
    $password = mysqli_real_escape_string($con, $_POST['password']);

    $sql = "INSERT INTO usuario (email, nome, cpf, senha) VALUES (?, ?, ?, ?)";
    $stmt = mysqli_prepare($con, $sql);
    mysqli_stmt_bind_param($stmt, 'ssss', $email, $nome, $cpf, $password);

    if (mysqli_stmt_execute($stmt)) {
        echo json_encode(['success' => true]);
    } else {
        echo json_encode(['success' => false, 'message' => 'Erro ao registrar no banco de dados.']);
    }

    mysqli_stmt_close($stmt);
    mysqli_close($con);
} else {
    echo json_encode(['success' => false, 'message' => 'Dados incompletos.']);
}
?>
