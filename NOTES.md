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

## Session 3 (date) — Migration @login_required

### À faire
- Ajouter helper session_utilisateur(request)
- Remplacer if not request.session.get("id_utilisateur")
  par @login_required (progressivement)
- Tester chaque modification

### Commandes utiles au démarrage
cd /c/Projet_Tiers_Payant
source venv/Scripts/activate
git status
python manage.py check

## Session 4 (29/09/2026) — Refactor en modules

### Fait
- Créé core/views/ (package Python)
- Renommé views.py → views_old.py (méthode safe)
- Migré 3 modules :
  - auth.py (connexion, deconnexion)
  - accueil.py (tableau de bord)
  - utilisateurs.py (utilisateurs, utilisateur_create, utilisateur_modifier, utilisateur_roles)
- Résolu boucle de redirection infinie
- Détecté et réparé faille .gitignore

### Méthode de migration
1. Créer le nouveau module avec les fonctions complètes
2. Vérifier check
3. Supprimer de views_old.py
4. Mettre à jour __init__.py
5. Tester
6. Commit

### À retenir
- Toujours vérifier git status avant commit
- Ne JAMAIS faire git add .
- Toujours 2 lignes vides entre fonctions
- Le .gitignore doit être versionné

### Modules restants à migrer (16)
roles, adherents, souscripteurs, contrats, garanties, actes,
adhesions, ayant_droit, prestataires, conventions, demandes_tp,
prises_en_charge, consommations, factures, reglements, recours,
documents, plafonds

### Prochaine session
- Migrer roles.py + adherents.py + souscripteurs.py
- Puis contrats.py + garanties.py

## Session 5 (29/09/2026) — Migration 5 modules

### Fait
- Migration de 5 modules (34 fonctions) :
  - roles.py (5 fonctions)
  - adherents.py (7 fonctions)
  - souscripteurs.py (5 fonctions)
  - contrats.py (7 fonctions)
  - garanties.py (10 fonctions, en 2 blocs)

### Méthode validée
1. Extraire le corps avec sed
2. Créer le fichier avec les imports
3. python manage.py check
4. Supprimer de views_old.py
5. Mettre à jour __init__.py
6. Tester
7. Commit

### Progression
- 8 modules / 19 migrés
- 41 fonctions migrées
- views_old.py passe de 9668 → ~5800 lignes

### À retenir
- Attention aux décorateurs (parfois laissés dans views_old.py)
- Supprimer les blocs du bas en premier (sinon décalage)
- Toujours tester après chaque étape
