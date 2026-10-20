# 📘 Installation — SAGPS Tiers Payant

Plateforme de gestion des prestations de santé.

## 🌐 Accès

- **URL** : http://192.168.0.215:8000
- **Réseau** : Local (intranet SAGPS)

## 🔧 Services Docker

| Nom | Port | Rôle |
|-----|------|------|
| `sagps-production` | 8000 | Application Django |
| `sagps-tier-payan-sagpsdb-rwm3kk` | 5432 | PostgreSQL 16 |

## 🚀 Commandes utiles

### Redémarrer
```bash
sudo docker restart sagps-production