function gravar() {
    var form = document.getElementById("formCadastro");
    var nome = document.getElementById("nome").value;
    var cpf = document.getElementById("cpf").value;
    var email = document.getElementById("email").value;
    var password = document.getElementById("password").value;
    var passwordConfirm = document.getElementById("passwordconfirm").value;


    var hashedPassword = CryptoJS.SHA256(password).toString();
    var hashedPasswordconfirm = CryptoJS.SHA256(passwordConfirm).toString();

    if (hashedPassword !== hashedPasswordconfirm) {
        alert("As senhas não são iguais.");
        return;
    }

    var dados = new FormData(form);
    dados.set('password', hashedPassword);
    dados.delete('passwordconfirm');

    fetch("../php/insere-registro.php", {
        method: "POST",
        body: dados
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = "../pages/login.html";
        } else {
            alert("Erro ao registrar: " + data.message);
        }
    }).catch(error => {
        alert("Erro ao processar o registro: " + error);
    });
}