fetch("../php/show-carrinho.php", {
    method: "GET"
}).then(async function(resposta){

    var dados = await resposta.json();

    listarCarrinho(dados);

    

});

fetch("../php/total-carrinho.php", {
    method: "GET"
}).then(async function(resposta){

    var dados = await resposta.json();

    var total = "";
    total +='Total: R$ ' + dados + ',00';

    document.getElementById("valorTotal").innerHTML += total;

})

function listarCarrinho(dados){

    for(var i = 0; i < dados.length; i++){

        var conteudo = "";
        conteudo += '<div class="carrinhoCard">';
        conteudo += '<div class="carrinhoNome">' + dados[i].nome + '</div>';
        conteudo += '<div class="carrinhoVal">R$ ' + dados[i].valor + ',00</div>';
        conteudo += '</div>';

        document.getElementById("listaCarrinho").innerHTML += conteudo

    }

}

function limparCarrinho(){
    fetch("../php/clear-carrinho.php", {
        method: "GET"
    }).then(window.location.reload());
}

function gotoProducts(){
    window.location.href = "../pages/products.html"
}

function gotoIndex(){
    window.location.href = "../index/index.html"
}

function gotoCart(){
    window.location.href = "../pages/cart.html"
}