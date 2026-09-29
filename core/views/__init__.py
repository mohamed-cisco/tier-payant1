"""Package des vues de l'application core.

Pendant la migration, toutes les vues sont réexportées depuis
views_old.py. Une fois la migration terminée, ce fichier importera
les vues depuis leurs modules respectifs.
"""

# Pour l'instant, on réexporte TOUT depuis views_old
from core.views_old import *  # noqa
