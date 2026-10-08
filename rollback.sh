#!/bin/bash

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${RED}═══════════════════════════════════════════════════${NC}"
echo -e "${RED}   ⚠️  ROLLBACK — RESTAURATION D'UN BACKUP${NC}"
echo -e "${RED}═══════════════════════════════════════════════════${NC}"
echo ""

# Lister les backups disponibles
echo -e "${YELLOW}📋 Backups disponibles :${NC}"
echo ""

BACKUPS=($(ls -d backups/pre_deploy_* 2>/dev/null | sort -r))

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo -e "${RED}❌ Aucun backup trouvé${NC}"
    exit 1
fi

for i in "${!BACKUPS[@]}"; do
    echo "  [$i] ${BACKUPS[$i]}"
done

echo ""
read -p "Quel backup restaurer ? (numéro) : " NUM

if [ -z "${BACKUPS[$NUM]}" ]; then
    echo -e "${RED}❌ Choix invalide${NC}"
    exit 1
fi

SELECTED="${BACKUPS[$NUM]}"

echo ""
echo -e "${YELLOW}⚠️  Vous allez restaurer : $SELECTED${NC}"
read -p "Confirmer ? (o/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
    echo -e "${RED}❌ Rollback annulé${NC}"
    exit 1
fi

# Restauration
echo ""
echo -e "${YELLOW}🔄 Restauration en cours...${NC}"

# 1. Base de données
if [ -f "$SELECTED/db.sql" ]; then
    echo -e "${YELLOW}💾 Restauration base de données...${NC}"
    PG_RESTORE="/c/Program Files/PostgreSQL/16/bin/psql.exe"
    "$PG_RESTORE" -U postgres -d tiers_payant -f "$SELECTED/db.sql" 2>/dev/null
    echo -e "${GREEN}✅ Base restaurée${NC}"
fi

# 2. Media
if [ -f "$SELECTED/media.tar.gz" ]; then
    echo -e "${YELLOW}📦 Restauration media...${NC}"
    tar -xzf "$SELECTED/media.tar.gz"
    echo -e "${GREEN}✅ Media restauré${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Rollback terminé !${NC}"
echo ""
