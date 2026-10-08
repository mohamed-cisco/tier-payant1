#!/bin/bash

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔒 Backup avant déploiement${NC}"

# Variables
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/pre_deploy_$DATE"
DB_NAME="tiers_payant"
DB_USER="postgres"

# Créer le dossier
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}📁 Dossier créé : $BACKUP_DIR${NC}"

# 1. Backup base de données
echo -e "${YELLOW}💾 Sauvegarde de la base de données...${NC}"
"/c/Program Files/PostgreSQL/16/bin/pg_dump.exe" -U $DB_USER $DB_NAME > "$BACKUP_DIR/db.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Base de données sauvegardée${NC}"
else
    echo -e "${RED}❌ Erreur sauvegarde base${NC}"
    exit 1
fi

# 2. Backup media
echo -e "${YELLOW}📦 Sauvegarde des fichiers media...${NC}"
tar -czf "$BACKUP_DIR/media.tar.gz" media/ 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Media sauvegardé${NC}"
else
    echo -e "${YELLOW}⚠️  Pas de media à sauvegarder${NC}"
fi

# 3. Backup code
echo -e "${YELLOW}📂 Sauvegarde du code...${NC}"
cp -r core "$BACKUP_DIR/core_backup"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Code sauvegardé${NC}"
else
    echo -e "${RED}❌ Erreur sauvegarde code${NC}"
    exit 1
fi

# Résumé
echo ""
echo -e "${GREEN}🎉 Backup terminé avec succès !${NC}"
echo -e "${GREEN}📁 Emplacement : $BACKUP_DIR${NC}"
echo ""
echo "Contenu du backup :"
ls -lh "$BACKUP_DIR"
