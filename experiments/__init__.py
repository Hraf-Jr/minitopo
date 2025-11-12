import os
import pkgutil
import importlib

from core.experiment import Experiment

# Dictionnaire public: nom d'expérience -> classe
EXPERIMENTS = {}

# Import dynamique de tous les sous-modules du package 'experiments'
_pkg_dir = os.path.dirname(__file__)
for _loader, _name, _ispkg in pkgutil.iter_modules([_pkg_dir]):
    importlib.import_module(f"{__name__}.{_name}")

def _register_all_subclasses(base_cls):
    # Enregistre récursivement toutes les sous-classes qui ont un attribut NAME
    for cls in base_cls.__subclasses__():
        if hasattr(cls, "NAME") and isinstance(getattr(cls, "NAME"), str):
            EXPERIMENTS[cls.NAME] = cls
        _register_all_subclasses(cls)

# Peupler EXPERIMENTS à partir des classes importées
_register_all_subclasses(Experiment)

# Override explicite: utiliser l'implémentation quiche pour xpType 'quic'
from .quic1 import QuicheHTTP3
EXPERIMENTS["quic"] = QuicheHTTP3
