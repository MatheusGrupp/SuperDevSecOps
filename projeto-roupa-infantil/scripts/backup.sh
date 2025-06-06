#!/bin/bash

# SuperDevSecOps Backup Script

set -e

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="superdevsecops_backup_${TIMESTAMP}"

echo "🔄 Starting backup process..."

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Backup databases
echo "📊 Backing up databases..."
docker-compose exec -T auth-db pg_dump -U auth_user authdb > "${BACKUP_DIR}/${BACKUP_NAME}/authdb.sql"
docker-compose exec -T task-db pg_dump -U task_user taskdb > "${BACKUP_DIR}/${BACKUP_NAME}/taskdb.sql"

# Backup Redis
echo "💾 Backing up Redis..."
docker-compose exec -T redis redis-cli SAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb "${BACKUP_DIR}/${BACKUP_NAME}/redis.rdb"

# Backup uploaded files (if any)
echo "📁 Backing up uploaded files..."
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/uploads"
# Add commands to backup uploaded files if applicable

# Backup configuration files
echo "⚙️ Backing up configuration..."
cp .env "${BACKUP_DIR}/${BACKUP_NAME}/.env.backup"

# Create tarball
echo "📦 Creating archive..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

echo "✅ Backup completed: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# Cleanup old backups (keep last 7 days)
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +7 -delete

echo "🧹 Old backups cleaned up"