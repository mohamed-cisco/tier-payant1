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

## Session 2 (28/09/2026) — Utilisateur Django custom

### Fait
- Utilisateur hérite de AbstractBaseUser + PermissionsMixin
- UtilisateurManager avec create_user/create_superuser
- AUTH_USER_MODEL = 'core.Utilisateur'
- Migration régénérée + base recréée (45 tables)
- Vue connexion → authenticate() + login()
- Vue deconnexion → logout()
- Session custom conservée pour compatibilité

### Tests
- Connexion OK
- Tableau de bord OK
- Déconnexion OK

### Prochaine étape
- Adapter progressivement les vues : @login_required au lieu de if session
- Mapper Role → Group Django
