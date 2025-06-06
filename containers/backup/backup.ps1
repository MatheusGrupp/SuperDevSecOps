$date = (Get-Date).ToString('yyyy-MM-dd')


# 1. Faz checagem se o Docker esta instalado

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "`nERROR" -ForegroundColor Red -NoNewline
    Write-Host " : Docker não está instalado."
    exit 1
}



# 2. Checa se o Docker esta rodando

try {
    docker info | Out-Null
} catch {
    Write-Host "`nERROR" -ForegroundColor Red -NoNewline
    Write-Host " : Docker não está em execução."
    exit 1
}

Write-Host ""
Write-Host "-----------------------------"
Write-Host "Bem vindo ao centro de Backup do DataBase!"
Write-Host "-----------------------------"
Write-Host ""
Write-Host " (1) Fazer o Backup"
Write-Host " (2) Colocar o Backup em producao"
Write-Host ""
$escolha = Read-Host "="



# 3. Fazer o Backup

if ($escolha -eq '1') {
    Write-Host ""
    Write-Host "`nWARN" -ForegroundColor Yellow -NoNewline
    Write-Host ": 'Fazer o Backup' opcao selecionada"

    $backupVolume = ("backup-mysql-data-$date").Trim()

    docker volume create $backupVolume | Out-Null

    docker run -d `
        --name backup_mysql `
        -v mysql-data:/mnt/mysql `
        -v ${backupVolume}:/mnt/backup `
        --network backup_mysql_network-R94 `
        --ip 10.0.94.10 `
        mysql:latest `
        bash -c "mysqldump -h 10.0.94.11 -u root -ppasswd --databases db > /mnt/backup/mysql-backup.sql"

    docker stop backup_mysql
    docker rm backup_mysql

    Write-Host "`nINFO" -ForegroundColor Blue -NoNewline
    Write-Host " : backup volume '$backupVolume' criado"

}



# 4. Replace 'mysql-data' data to backup-mysql-data-$date

elseif ($escolha -eq '2') {
    Write-Host "`nWARN" -ForegroundColor Yellow -NoNewline
    Write-Host " : 'Colocar o Backup em Producao' option selected"

    # Retorna os volumes de backup disponíveis e permite escolha
    Write-Host "`nSelecione algum backup de volume para restaurar em produção:"
    $volumeNames = @(docker volume ls -q | Where-Object { $_ -like "*backup-mysql*" })
    Write-Host "Volumes encontrados:"
    for ($i=0; $i -le $volumeNames.Length - 1; $i=$i+1 ) {
        Write-Host "($i) - " ${volumeNames}[$i];
    }

    $backup_chosed = Read-Host "Qual backup deseja escolher?`n="
    $backup_chosed = ${volumeNames}[$backup_chosed]

    Write-Host "`nWARN" -ForegroundColor Yellow -NoNewline
    Write-Host " : Trocando dados atuais MySQL com '$backup_chosed'"

    docker exec -i mysql_stable mysql -u root -ppasswd `
        -e "DROP DATABASE IF EXISTS db; CREATE DATABASE db;"

    docker run -d `
        --name backup_mysql `
        -v mysql-data:/mnt/mysql `
        -v ${backup_chosed}:/mnt/backup `
        --network backup_mysql_network-R94 `
        --ip 10.0.94.10 `
        mysql:latest `
        bash -c "mysql -h 10.0.94.11 -u root -ppasswd db < /mnt/backup/mysql-backup.sql" | Out-Null

    docker stop backup_mysql | Out-Null
    docker rm backup_mysql   | Out-Null

    Write-Host "`nINFO" -ForegroundColor Blue -NoNewline
    Write-Host " : volume substitution concluded!"
}