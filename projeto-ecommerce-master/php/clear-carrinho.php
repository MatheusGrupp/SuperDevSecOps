<?php

include "conexao.php";

$sql = "DELETE FROM carrinho";

mysqli_query($con, $sql);