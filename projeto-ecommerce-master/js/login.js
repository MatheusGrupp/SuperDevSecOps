function login() {
    var email = document.getElementById("email").value;
    var password = document.getElementById("password").value;

    // Criptografar a senha com SHA256 usando CryptoJS
    var hashedPassword = CryptoJS.SHA256(password).toString();

    var dados = new FormData();
    dados.set('email', email);
    dados.set('password', hashedPassword);

    fetch("../php/login.php", {
        method: "POST",
        body: dados
    }).then(async function(response) {
        var dados = await response.json();

        if (dados.success) {
            window.location.href = "../index/index.html";
        } else {
            alert("Erro ao fazer login: " + dados.message);
        }
    }).catch(error => {
        alert("Erro ao processar o login: " + error);
    });
}