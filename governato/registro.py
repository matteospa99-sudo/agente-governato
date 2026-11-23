"""Registro delle attività, a prova di manomissione.

Ogni evento (una proposta, un blocco, un'approvazione) diventa una riga
in un file JSONL. Ogni riga contiene l'impronta (hash SHA-256) della riga
precedente: se qualcuno modifica o cancella una riga a posteriori,
la catena si spezza e verifica() lo segnala.

È lo stesso principio dei registri contabili: non impedisce di scrivere
il falso, ma rende visibile ogni correzione fatta dopo.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ORIGINE = "0" * 64  # impronta convenzionale prima del primo evento


def _impronta(dati: dict) -> str:
    testo = json.dumps(dati, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


class Registro:
    def __init__(self, percorso: str | Path):
        self.percorso = Path(percorso)
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        self._ultima = self._leggi_ultima_impronta()

    def _leggi_ultima_impronta(self) -> str:
        if not self.percorso.exists():
            return ORIGINE
        ultima = ORIGINE
        for riga in self.percorso.read_text(encoding="utf-8").splitlines():
            if riga.strip():
                ultima = json.loads(riga)["impronta"]
        return ultima

    def scrivi(self, tipo: str, chi: str, **dettagli) -> dict:
        evento = {
            "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tipo": tipo,          # es. "proposta", "bloccata", "approvata"
            "chi": chi,            # quale agente o componente
            "dettagli": dettagli,
            "precedente": self._ultima,
        }
        evento["impronta"] = _impronta(evento)
        with self.percorso.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
        self._ultima = evento["impronta"]
        return evento

    def eventi(self) -> list[dict]:
        if not self.percorso.exists():
            return []
        return [json.loads(r) for r in self.percorso.read_text(encoding="utf-8").splitlines() if r.strip()]

    def verifica(self) -> tuple[bool, str]:
        """Ricalcola la catena. Restituisce (integro, messaggio)."""
        precedente = ORIGINE
        for n, evento in enumerate(self.eventi(), start=1):
            if evento["precedente"] != precedente:
                return False, f"Catena spezzata alla riga {n}: manca o è stata spostata una riga."
            copia = {k: v for k, v in evento.items() if k != "impronta"}
            if _impronta(copia) != evento["impronta"]:
                return False, f"Riga {n} modificata dopo la scrittura."
            precedente = evento["impronta"]
        return True, "Registro integro."
