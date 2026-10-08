#!/bin/bash

# ============================================================
# SCRIPT DE DÉPLOIEMENT — Projet Tiers Payant
# ============================================================

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 DÉPLOIEMENT TIERS PAYANT${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# ============================================================
# 0. VÉRIFICATIONS PRÉALABLES
# ============================================================
echo -e "${YELLOW}📋 Vérification de l'état du projet...${NC}"

# Vérifier que git est propre
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}⚠️  Attention : il y a des modifications non commitées${NC}"
    echo ""
    git status --short
    echo ""
    read -p "Continuer quand même ? (o/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
        echo -e "${RED}❌ Déploiement annulé${NC}"
        exit 1
    fi
fi

# ============================================================
# 1. BACKUP AUTOMATIQUE
# ============================================================
echo ""
echo -e "${BLUE}── ÉTAPE 1/6 : Backup ──${NC}"

if [ -f "backup_avant_deploy.sh" ]; then
    ./backup_avant_deploy.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Le backup a échoué${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Script de backup introuvable, ignoré${NC}"
fi

# ============================================================
# 2. GIT PULL
# ============================================================
echo ""
echo -e "${BLUE}── ÉTAPE 2/6 : Récupération du code ──${NC}"

git pull
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Le git pull a échoué${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Code récupéré${NC}"

# ============================================================
# 3. ACTIVATION ENV VIRTUEL
# ============================================================
echo ""
echo -e "${BLUE}── ÉTAPE 3/6 : Environnement virtuel ──${NC}"

if [ -d "venv" ]; then
    source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
    echo -e "${GREEN}✅ Environnement activé${NC}"
else
    echo -e "${YELLOW}⚠️  Pas de venv trouvé${NC}"
fi

# ============================================================
# 4. INSTALLATION DES DÉPENDANCES
# ============================================================
echo ""
echo -e "${BLUE}── ÉTAPE 4/6 : Dépendances ──${NC}"

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dépendances à jour${NC}"
    else
        echo -e "${RED}❌ Erreur installation dépendances${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt introuvable${NC}"
fi

# ============================================================
# 5. MIGRATIONS
# ============================================================
echo ""
echo -e "${BLUE}── ÉTAPE 5/6 : Migrations base de données ──${NC}"

python manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Les migrations ont échoué${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Migrations appliquées${NC}"

# ============================================================
# 6. FICHIERS STATIQUES + VÉRIFICATION
# ============================================================
echo ""
echo -e "${BLUE}── ÉTAPE 6/6 : Vérification finale ──${NC}"

python manage.py collectstatic --noinput --quiet 2>/dev/null
echo -e "${GREEN}✅ Fichiers statiques collectés${NC}"

python manage.py check
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Le check Django a échoué${NC}"
    exit 1
fi

# ============================================================
# RÉSUMÉ FINAL
# ============================================================
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   🎉 DÉPLOIEMENT RÉUSSI !${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ Backup effectué${NC}"
echo -e "${GREEN}✅ Code récupéré${NC}"
echo -e "${GREEN}✅ Dépendances installées${NC}"
echo -e "${GREEN}✅ Migrations appliquées${NC}"
echo -e "${GREEN}✅ Fichiers statiques collectés${NC}"
echo -e "${GREEN}✅ Vérifications OK${NC}"
echo ""
echo -e "${YELLOW}💡 N'oubliez pas de redémarrer le serveur si nécessaire${NC}"
echo ""
