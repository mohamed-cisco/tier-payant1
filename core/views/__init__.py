"""Package des vues de l'application core.

Pendant la migration, les vues migrées sont importées depuis leur
module, et les autres sont encore réexportées depuis views_old.py.
"""

# Vues migrées (ordre : les plus spécifiques en premier)
from .auth import connexion, deconnexion  # noqa

# Vues pas encore migrées (réexport depuis views_old)
from core.views_old import *  # noqa
