<?php
include "conexao.php";

$sql = "SELECT * from carrinho";

$resultado = mysqli_query($con, $sql);

$i = 0;

while($registro = mysqli_fetch_assoc($resultado)) {
    $data[$i]["nome"] = $registro["nome"];
    $data[$i]["descricao"] = $registro["descricao"];
    $data[$i]["valor"] = $registro["valor"];
    $i++;

}

$objectjSON = json_encode($data);
echo $objectjSON;

?>