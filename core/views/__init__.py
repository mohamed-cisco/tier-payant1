"""Package des vues de l'application core.

Pendant la migration, les vues migrées sont importées depuis leur
module, et les autres sont encore réexportées depuis views_old.py.
"""

# Vues migrées (ordre : les plus spécifiques en premier)
from .auth import connexion, deconnexion  # noqa
from .accueil import accueil  # noqa
from .utilisateurs import (  # noqa
    utilisateurs,
    utilisateur_create,
    utilisateur_modifier,
    utilisateur_roles,
)
from .roles import (  # noqa
    roles,
    role_create,
    role_detail,
    role_permissions,
    role_modifier,
)
from .adherents import (  # noqa
    adherents,
    adherent_detail,
    adherent_create,
    adherent_modifier,
    adherent_radier,
)
from .souscripteurs import (  # noqa
    souscripteurs,
    souscripteur_create,
    souscripteur_modifier,
    souscripteur_radier,
)
from .contrats import (  # noqa
    contrats,
    contrat_detail,
    contrat_garantie_create,
    contrat_create,
    contrat_modifier,
    contrat_radier,
)
from .garanties import (  # noqa
    garanties,
    garantie_detail,
    garantie_create,
    garantie_modifier,
    garantie_radier,
    garantie_actes,
    garantie_acte_create,
    garantie_acte_modifier,
    garantie_acte_radier,
)
from .actes import (  # noqa
    actes,
    acte_detail,
    acte_create,
    acte_modifier,
    acte_radier,
    sous_actes,
    sous_acte_create,
    sous_acte_modifier,
    sous_acte_radier,
    tarifs_sous_actes,
    tarif_sous_acte_create,
    tarif_sous_acte_modifier,
    tarif_sous_acte_radier,
)

# Vues pas encore migrées (réexport depuis views_old)
from core.views_old import *  # noqa
