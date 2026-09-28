# Journal de bord — Projet Tiers Payant

## Session 1 (28/09/2026) — Refactor initial

### Fait
- Sauvegarde Git + GitHub (dépôt privé)
- Nettoyage models.py (-111 lignes)
- Ajout TextChoices pour statuts
- Passage à managed=True (36 modèles)
- Migration initiale + base recréée
- Sécurité : SECRET_KEY + mot de passe DB

### Prochaines étapes
- Utilisateur Django custom (AbstractBaseUser)
- Migration connexion → login()
- Refactor views.py en modules
