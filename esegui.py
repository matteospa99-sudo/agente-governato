"""Fa lavorare i due agenti sulla posta di prova.

Esempi:
  python esegui.py                          modello simulato, approvi tu dal terminale
  python esegui.py --approvazione nega      nessuna azione irreversibile passa
  python esegui.py --modello claude         modello vero (serve ANTHROPIC_API_KEY)
  python esegui.py --verifica               controlla che il registro non sia stato manomesso
"""

import argparse
from pathlib import Path

from governato import Casella, Governatore, Interruttore, Orchestratore, Registro
from governato import approva_sempre, approvatore_terminale, nega_sempre
from governato.modelli import ModelloClaude, ModelloIngenuo
from governato.strumenti import carica_email

CARTELLA = Path(__file__).parent


def scegli_modello(nome: str):
    if nome != "claude":
        return ModelloIngenuo()
    try:
        return ModelloClaude()
    except RuntimeError as errore:
        raise SystemExit(f"Modello vero non disponibile: {errore}")


def main():
    p = argparse.ArgumentParser(description="Agente governato: posta smistata sotto controllo.")
    p.add_argument("--modello", choices=["simulato", "claude"], default="simulato")
    p.add_argument("--approvazione", choices=["terminale", "nega", "approva"], default="terminale")
    p.add_argument("--posta", default=str(CARTELLA / "dati" / "posta.json"))
    p.add_argument("--registro", default=str(CARTELLA / "registro" / "attivita.jsonl"))
    p.add_argument("--verifica", action="store_true", help="verifica solo l'integrità del registro")
    a = p.parse_args()

    registro = Registro(a.registro)
    if a.verifica:
        integro, messaggio = registro.verifica()
        print(("OK  " if integro else "ERRORE  ") + messaggio)
        return

    approvatore = {"terminale": approvatore_terminale, "nega": nega_sempre, "approva": approva_sempre}[a.approvazione]
    casella = Casella(carica_email(a.posta))
    governatore = Governatore(Interruttore(CARTELLA / "ARRESTO"))
    orchestratore = Orchestratore(scegli_modello(a.modello), casella, registro, governatore, approvatore)

    esiti = orchestratore.tratta_tutte()

    print(f"\nModello: {orchestratore.nome_modello}")
    print(f"{'email':<6} {'categoria':<24} {'eseguite':<30} {'bloccate':<12} esito")
    for e in esiti:
        bloccate = ",".join(r for r, _ in e.bloccate) or "-"
        print(f"{e.email_id:<6} {str(e.categoria):<24} {','.join(e.eseguite) or '-':<30} {bloccate:<12} "
              f"{'DA RIVEDERE' if e.da_rivedere else 'ok'}")
    print(f"\nBozze: {len(casella.bozze)}  Inviate: {len(casella.inviate)}  Archiviate: {len(casella.archiviate)}")
    print(f"Registro: {a.registro}  ({registro.verifica()[1]})")


if __name__ == "__main__":
    main()
