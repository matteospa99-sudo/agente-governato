"""Il governatore: il punto in cui si decide che cosa un agente può fare.

Principio di fondo: il modello linguistico propone, il codice decide.
Le regole qui sotto sono codice ordinario, deterministico e verificabile.
Non dipendono dal fatto che il modello "capisca" o "obbedisca":
se un'email trappola convince il modello a proporre un'azione vietata,
la proposta viene fermata qui.

Ogni regola corrisponde a un controllo che si può citare in un'analisi
dei rischi (vedi docs/come-funziona.md):
  R1 interruttore di arresto
  R2 solo strumenti esistenti
  R3 minimo privilegio per agente
  R4 argomenti attesi e ben formati
  R5 l'agente agisce solo sull'email che sta trattando
  R6 risposte solo al mittente (niente destinatari terzi)
  R7 limite di lunghezza dei testi
  R8 limite di azioni per email
  R9 azioni irreversibili solo con approvazione umana
"""

from dataclasses import dataclass
from pathlib import Path

from .strumenti import STRUMENTI, Email

# Quali strumenti può chiedere ciascun agente (R3).
# Lo smistatore non ha strumenti: produce solo una classificazione.
PERMESSI: dict[str, frozenset[str]] = {
    "smistatore": frozenset(),
    "preparatore": frozenset({"etichetta", "prepara_bozza", "archivia", "invia_email"}),
}

CATEGORIE = ("richiesta_informazioni", "appuntamento", "reclamo", "spam", "altro")
PRIORITA = ("alta", "media", "bassa")

MAX_TESTO = 2000          # R7
MAX_AZIONI_PER_EMAIL = 4  # R8


class Interruttore:
    """Interruttore di arresto (R1).

    Si attiva da codice oppure creando un file chiamato ARRESTO
    nella cartella del progetto: utile perché una persona può fermare
    il sistema senza toccare il codice.
    """

    def __init__(self, file_arresto: str | Path = "ARRESTO"):
        self.file_arresto = Path(file_arresto)
        self._attivo = False

    def attiva(self):
        self._attivo = True

    @property
    def attivo(self) -> bool:
        return self._attivo or self.file_arresto.exists()


@dataclass
class Decisione:
    esito: str    # "consentita", "serve_approvazione", "bloccata"
    regola: str   # quale regola ha deciso
    motivo: str


def valida_smistamento(messaggio) -> tuple[bool, str]:
    """Controlla il messaggio che lo smistatore passa al preparatore.

    È il punto di controllo tra i due agenti. Il messaggio può contenere
    solo due campi, con valori presi da elenchi chiusi. Così un'istruzione
    nascosta in un'email non può viaggiare da un agente all'altro:
    non c'è nessun campo di testo libero in cui infilarla.
    """
    if not isinstance(messaggio, dict):
        return False, "Il messaggio non è un oggetto strutturato."
    if set(messaggio) != {"categoria", "priorita"}:
        return False, f"Campi non ammessi o mancanti: {sorted(messaggio)}."
    if messaggio["categoria"] not in CATEGORIE:
        return False, f"Categoria sconosciuta: {messaggio['categoria']!r}."
    if messaggio["priorita"] not in PRIORITA:
        return False, f"Priorità sconosciuta: {messaggio['priorita']!r}."
    return True, "Messaggio valido."


class Governatore:
    def __init__(self, interruttore: Interruttore | None = None):
        self.interruttore = interruttore or Interruttore()
        self._conteggio: dict[str, int] = {}

    def valuta(self, agente: str, proposta, email: Email) -> Decisione:
        """Decide su una singola azione proposta da un agente."""

        def blocca(regola, motivo):
            return Decisione("bloccata", regola, motivo)

        if self.interruttore.attivo:
            return blocca("R1", "Interruttore di arresto attivo.")

        if not isinstance(proposta, dict) or set(proposta) != {"strumento", "argomenti"}:
            return blocca("R4", "La proposta non ha la forma {strumento, argomenti}.")

        nome = proposta["strumento"]
        argomenti = proposta["argomenti"]

        if nome not in STRUMENTI:
            return blocca("R2", f"Strumento inesistente: {nome!r}.")

        if nome not in PERMESSI.get(agente, frozenset()):
            return blocca("R3", f"L'agente '{agente}' non è autorizzato a usare '{nome}'.")

        scheda = STRUMENTI[nome]
        if not isinstance(argomenti, dict) or set(argomenti) != set(scheda.argomenti):
            return blocca("R4", f"Argomenti attesi: {list(scheda.argomenti)}.")
        if not all(isinstance(v, str) for v in argomenti.values()):
            return blocca("R4", "Tutti gli argomenti devono essere testo.")

        if argomenti["email_id"] != email.id:
            return blocca("R5", "L'azione riguarda un'email diversa da quella in lavorazione.")

        if "destinatario" in argomenti and argomenti["destinatario"].strip().lower() != email.mittente.lower():
            return blocca("R6", f"Destinatario {argomenti['destinatario']!r} diverso dal mittente.")

        if len(argomenti.get("testo", "")) > MAX_TESTO:
            return blocca("R7", f"Testo oltre {MAX_TESTO} caratteri.")

        fatte = self._conteggio.get(email.id, 0)
        if fatte >= MAX_AZIONI_PER_EMAIL:
            return blocca("R8", f"Superato il limite di {MAX_AZIONI_PER_EMAIL} azioni per email.")
        self._conteggio[email.id] = fatte + 1

        if not scheda.reversibile:
            return Decisione("serve_approvazione", "R9", "Azione irreversibile: decide una persona.")

        return Decisione("consentita", "-", "Azione reversibile e conforme alle regole.")
