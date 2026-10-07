# core/views/__init__.py
"""
Package des vues de la plateforme Tiers Payant.

Tous les modules sont maintenant migrés.

Import dans l'ordre pour éviter les dépendances circulaires.
"""

# ============================================================
# MODULES DE BASE (pas de dépendances)
# ============================================================
from .decorators import *
from .dashboard import *
from .champs import *
from .backup import *
from .ajax import *


# ============================================================
# MODULES MÉTIER
# ============================================================

# Authentification
from .auth import *

# Adhérents + Ayants droit + Adhésions
from .adherents import *
from .ayants_droit import *
from .adhesions import *

# Souscripteurs + Contrats + Garanties
from .souscripteurs import *
from .contrats import *
from .garanties import *
from .garantie_actes import *
from .plafonds import *

# Actes + Prestataires
from .actes import *
from .prestataires import *

# Workflow TP (le cœur)
from .demandes_tp import *
from .pec import *
from .consommations import *
from .factures import *
from .reglements import *

# Recours + Documents
from .recours import *
from .documents import *

# Administration
from .admin import *
# Rapports
from .rapports import *


# ============================================================
# VÉRIFICATION : TOUS LES MODULES DOIVENT ÊTRE IMPORTÉS
# ============================================================
print("✅ Tous les modules de core.views importés")