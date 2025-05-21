function gotoProducts(){
    window.location.href = "../pages/products.html"
}

function gotoIndex(){
    window.location.href = "../index/index.html"
}

function gotoCart(){
    window.location.href = "../pages/cart.html"
}

var data = fetch("../php/show-products.php", {
    method: "GET"
    }).then(async function(resposta) {

    var data= await resposta.json();

    listarProdutos(data, 0, "cycloneInfo");
    listarProdutos(data, 1, "boneInfo");
    listarProdutos(data, 2, "messiInfo");
    listarProdutos(data, 3, "kennerInfo");
    listarProdutos(data, 4, "correnteInfo");
    listarProdutos(data, 5, "julietInfo");
    
    return data;
});

console.log(data);

function listarProdutos(data, i, id){

    var conteudo = "";
    conteudo += '<div class="produtosNome">' + data[i].nome + '</div>';
    conteudo += '<div class="produtosDesc">' + data[i].descricao + '</div>';
    conteudo += '<div class="produtosVal">R$ ' + data[i].valor + ',00</div>';

    document.getElementById(id).innerHTML += conteudo

}

function adicionarCarrinho(id){

    var form = document.getElementById(id);
    var dados = new FormData(form);
    
    fetch("../php/insere-carrinho.php", {
        method: "POST",
        body: dados
        })

}


