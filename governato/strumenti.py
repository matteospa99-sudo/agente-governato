"""Gli strumenti che gli agenti possono chiedere di usare.

Una casella di posta finta, in memoria, con dati inventati.
Ogni strumento ha una scheda che dice due cose che contano per la governance:
- se l'azione è reversibile (una bozza si cancella, un invio no);
- quale agente può chiederla (minimo privilegio).

Gli agenti non chiamano mai queste funzioni direttamente:
le chiamate passano sempre dal governatore (politiche.py).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Email:
    id: str
    mittente: str
    oggetto: str
    corpo: str


def carica_email(percorso: str | Path) -> list[Email]:
    """Legge un file JSON di email (i campi in più, come 'tipo', sono ignorati)."""
    righe = json.loads(Path(percorso).read_text(encoding="utf-8"))
    return [Email(r["id"], r["mittente"], r["oggetto"], r["corpo"]) for r in righe]


@dataclass
class Casella:
    """Casella di posta simulata. Nessuna email esce davvero."""
    in_arrivo: list[Email]
    bozze: list[dict] = field(default_factory=list)
    inviate: list[dict] = field(default_factory=list)
    archiviate: list[str] = field(default_factory=list)
    etichette: dict[str, str] = field(default_factory=dict)

    def trova(self, email_id: str) -> Email | None:
        return next((e for e in self.in_arrivo if e.id == email_id), None)


# --- Le funzioni vere e proprie -------------------------------------------

def etichetta(casella: Casella, email_id: str, etichetta: str) -> str:
    casella.etichette[email_id] = etichetta
    return f"Email {email_id} etichettata come '{etichetta}'."


def prepara_bozza(casella: Casella, email_id: str, destinatario: str, testo: str) -> str:
    casella.bozze.append({"email_id": email_id, "destinatario": destinatario, "testo": testo})
    return f"Bozza preparata per {destinatario}."


def archivia(casella: Casella, email_id: str) -> str:
    casella.archiviate.append(email_id)
    return f"Email {email_id} archiviata."


def invia_email(casella: Casella, email_id: str, destinatario: str, testo: str) -> str:
    casella.inviate.append({"email_id": email_id, "destinatario": destinatario, "testo": testo})
    return f"Email inviata a {destinatario}."


# --- Le schede degli strumenti --------------------------------------------

@dataclass(frozen=True)
class Scheda:
    funzione: callable
    reversibile: bool
    argomenti: tuple[str, ...]
    descrizione: str


STRUMENTI: dict[str, Scheda] = {
    "etichetta": Scheda(etichetta, True, ("email_id", "etichetta"),
                        "Assegna un'etichetta a un'email."),
    "prepara_bozza": Scheda(prepara_bozza, True, ("email_id", "destinatario", "testo"),
                            "Prepara una risposta in bozza. Non invia nulla."),
    "archivia": Scheda(archivia, True, ("email_id",),
                       "Sposta un'email in archivio."),
    "invia_email": Scheda(invia_email, False, ("email_id", "destinatario", "testo"),
                          "Invia un'email. Irreversibile."),
}
