"""Agente governato: due agenti AI che lavorano sulla posta sotto controlli verificabili."""

from .orchestratore import Orchestratore, approva_sempre, approvatore_terminale, nega_sempre
from .politiche import Governatore, Interruttore
from .registro import Registro
from .strumenti import Casella, Email

__all__ = ["Orchestratore", "Governatore", "Interruttore", "Registro", "Casella", "Email",
           "approvatore_terminale", "nega_sempre", "approva_sempre"]
