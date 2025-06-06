
<?php
$con = mysqli_connect($_ENV["MYSQL_HOSTNAME"], $_ENV["MYSQL_USER"], $_ENV["MYSQL_PASSWORD"], $_ENV["MYSQL_DATABASE"]);

if (!$con) {
    die("Connection failed: " . mysqli_connect_error());
}
?>

