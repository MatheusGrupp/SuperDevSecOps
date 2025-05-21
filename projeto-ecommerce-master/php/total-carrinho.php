<?php
include "conexao.php";

$sql = "SELECT SUM(valor) AS value_sum FROM carrinho";

$result = mysqli_query($con, $sql);
$row = mysqli_fetch_assoc($result);
$sum = $row['value_sum'];

$objectjSON = json_encode($sum);
echo $objectjSON;

?>