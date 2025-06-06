#!/usr/bin/env bash

date=$(date '+%Y-%m-%d')

# ANSI color codes
RED="\e[31m"
BLUE="\e[34m"
YELLOW="\e[33m"
NC="\e[0m"



# 1. Checa se o Dockre esta instalado

if ! command -v docker &> /dev/null; then
  echo -e "${RED}ERROR${NC}: Docker nao esta instalado."
  exit 1
fi



# 2. Check se o Docker esta rodando

if ! docker info &> /dev/null; then
  echo -e "${RED}ERROR${NC}: Docker nao esta rodando."
  exit 1
fi

echo -e '\n-----------------------------\n!\n-----------------------------'
read -rp $' (1) Fazer o Backup\n (2) Colocar o Backup em Producao\n\n=' escolha



# 3. Fazer o Backup

if [[ "$escolha" -eq "1" ]]; then
    echo -e "\n\n\n${YELLOW}WARN${NC}: 'Fazer o Backup' option selected"
    docker volume create backup-mysql-data-$date &> /dev/null

    docker run -d \
      --name backup_mysql \
      -v mysql-data:/mnt/mysql \
      -v backup-mysql-data-$date:/mnt/backup \
      --network backup_mysql_network-R94 \
      --ip 10.0.94.10 \
      mysql:latest \
      bash -c "mysqldump -h 10.0.94.11 -u root -ppasswd --databases db > /mnt/backup/mysql-backup.sql"

    docker stop backup_mysql &> /dev/null || true
    docker rm backup_mysql &> /dev/null || true  
    
    echo -e "\n${BLUE}INFO${NC}: backup volume 'backup-mysql-data-$date' created"



  # 4. Replace 'mysql-data' data to backup-mysql-data-$date

  elif [[ "$escolha" -eq "2" ]]; then
    echo -e "\n${YELLOW}WARN${NC}: 'Fazer o Backup' option selected"
    readarray -t array_docker_volume < <(docker volume ls -q | grep "backup-mysql-data")



    # Retorna os volumes de backup disponíveis e permite escolha
    echo -e "\nSelecione algum backup de volume para adicionar em produção:"
    for volume_index in "${!array_docker_volume[@]}"
    do
      echo "($volume_index) - ${array_docker_volume[$volume_index]}"
    done
    read -rp $'\n=' escolha



    # Start the prod replace to backup
    echo -e "\n${YELLOW}WARN${NC}: Trocando os dados atuais MySQL para '${array_docker_volume[$escolha]}'"
    
    docker exec -i mysql_stable mysql -u root -ppasswd -e "DROP DATABASE db; CREATE DATABASE db;"

    docker run -d \
      --name backup_mysql \
      -v mysql-data:/mnt/mysql \
      -v ${array_docker_volume[$escolha]}:/mnt/backup \
      --network backup_mysql_network-R94 \
      --ip 10.0.94.10 \
      mysql:latest \
      bash -c "mysql -h 10.0.94.11  -u root -ppasswd db < /mnt/backup/mysql-backup.sql"

    docker stop backup_mysql &> /dev/null || true
    docker rm backup_mysql &> /dev/null || true
    
    echo -e "\n${BLUE}INFO${NC}: volume substitution concluded!"
fi

# 