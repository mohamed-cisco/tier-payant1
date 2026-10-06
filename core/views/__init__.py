# core/views/__init__.py
"""
Package des vues de la plateforme Tiers Payant.

Stratégie de migration progressive :
1. On importe TOUT depuis views_old.py (compatibilité)
2. On migre progressivement chaque module
3. Une fois TOUT migré, on supprime l'import de views_old
"""

# ============================================================
# IMPORT DE L'ANCIEN FICHIER (pour compatibilité)
# ============================================================
from core.views_old import *


# ============================================================
# NOUVEAUX MODULES (à décommenter au fur et à mesure)
# ============================================================

# Module auth (déjà migré, mais en conflit avec views_old)
# from .auth import *   ← On le décommentera à la fin

# Module backup
# from .backup import *

# Module champs
# from .champs import *

# Module dashboard
# from .dashboard import *

# Module ajax
# from .ajax import *

# Module souscripteurs
# from .souscripteurs import *

# Module adherents
# from .adherents import *

# Module contrats
# from .contrats import *

# Module actes
# from .actes import *

# Module prestataires
# from .prestataires import *

# Module admin
# from .admin import *

# Module recours
# from .recours import *

# Module documents
# from .documents import *

# Module demandes_tp
# from .demandes_tp import *

# Module pec
# from .pec import *

# Module consommations
# from .consommations import *

# Module factures
# from .factures import *

# Module reglements
# from .reglements import *

# Module pdf
# from .pdf import *