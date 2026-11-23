"""L'orchestratore: mette in fila agenti, governatore, persona e registro.

Per ogni email:
  1. lo smistatore classifica;
  2. il messaggio tra i due agenti passa dal punto di controllo (C1);
  3. il preparatore propone le azioni;
  4. il governatore decide su ciascuna (R1-R9);
  5. le azioni irreversibili vanno a una persona, che approva o nega;
  6. tutto finisce nel registro.

Se qualcosa non torna (risposta illeggibile, messaggio non valido,
azione bloccata), l'email riceve l'etichetta "da_rivedere":
il sistema, nel dubbio, si ferma e lascia la decisione a una persona.
"""

from dataclasses import dataclass, field

from .agenti import Preparatore, Smistatore
from .politiche import Governatore, valida_smistamento
from .registro import Registro
from .strumenti import STRUMENTI, Casella, Email


# --- Chi approva le azioni irreversibili ----------------------------------

SEGNALI_DI_PRESSIONE = ("urgente", "subito", "oggi stesso", "bonifico", "pagamento", "password", "riservat")


def approvatore_terminale(email: Email, proposta: dict) -> bool:
    a = proposta["argomenti"]
    print("\n--- RICHIESTA DI APPROVAZIONE ---")
    testo_email = (email.oggetto + " " + email.corpo).lower()
    segnali = [s for s in SEGNALI_DI_PRESSIONE if s in testo_email]
    if segnali:
        # La persona è l'ultimo controllo: le si mostra perché fermarsi a pensare.
        print(f"ATTENZIONE: l'email contiene segnali tipici delle truffe ({', '.join(segnali)}).")
    print(f"Email: {email.id} da {email.mittente} - {email.oggetto}")
    print(f"Azione: {proposta['strumento']} a {a.get('destinatario')}")
    print(f"Testo: {a.get('testo')}")
    return input("Approvi? [s/N] ").strip().lower() == "s"


def nega_sempre(email: Email, proposta: dict) -> bool:
    return False


def approva_sempre(email: Email, proposta: dict) -> bool:
    return True


# --- Esito di una email ---------------------------------------------------

@dataclass
class Esito:
    email_id: str
    categoria: str | None = None
    eseguite: list[str] = field(default_factory=list)
    bloccate: list[tuple[str, str]] = field(default_factory=list)   # (regola, motivo)
    approvazioni: list[tuple[str, bool]] = field(default_factory=list)
    da_rivedere: bool = False


class Orchestratore:
    def __init__(self, modello, casella: Casella, registro: Registro,
                 governatore: Governatore | None = None, approvatore=nega_sempre):
        self.smistatore = Smistatore(modello)
        self.preparatore = Preparatore(modello)
        self.casella = casella
        self.registro = registro
        self.governatore = governatore or Governatore()
        self.approvatore = approvatore
        self.nome_modello = getattr(modello, "nome", "sconosciuto")

    def _da_rivedere(self, esito: Esito, motivo: str):
        esito.da_rivedere = True
        self.casella.etichette[esito.email_id] = "da_rivedere"
        self.registro.scrivi("da_rivedere", "orchestratore", email_id=esito.email_id, motivo=motivo)

    def _esegui(self, proposta: dict, esito: Esito):
        scheda = STRUMENTI[proposta["strumento"]]
        risultato = scheda.funzione(self.casella, **proposta["argomenti"])
        esito.eseguite.append(proposta["strumento"])
        self.registro.scrivi("eseguita", "orchestratore", email_id=esito.email_id,
                             strumento=proposta["strumento"], risultato=risultato)

    def tratta(self, email: Email) -> Esito:
        esito = Esito(email.id)
        self.registro.scrivi("ricevuta", "orchestratore", email_id=email.id,
                             mittente=email.mittente, oggetto=email.oggetto, modello=self.nome_modello)

        # 1-2. Smistamento e punto di controllo tra agenti
        smistamento, grezzo = self.smistatore.lavora(email)
        self.registro.scrivi("proposta", "smistatore", email_id=email.id, contenuto=grezzo)
        valido, motivo = valida_smistamento(smistamento)
        if not valido:
            esito.bloccate.append(("C1", motivo))
            self.registro.scrivi("bloccata", "punto_di_controllo", email_id=email.id, regola="C1", motivo=motivo)
            self._da_rivedere(esito, "Messaggio tra agenti non valido.")
            return esito
        esito.categoria = smistamento["categoria"]
        self.registro.scrivi("messaggio_tra_agenti", "punto_di_controllo", email_id=email.id, contenuto=smistamento)

        # 3. Proposte del preparatore
        proposte, grezzo = self.preparatore.lavora(email, smistamento)
        self.registro.scrivi("proposta", "preparatore", email_id=email.id, contenuto=grezzo)
        if not isinstance(proposte, list):
            self._da_rivedere(esito, "Risposta del preparatore illeggibile.")
            return esito

        # 4-5. Decisione su ciascuna proposta
        for proposta in proposte:
            decisione = self.governatore.valuta("preparatore", proposta, email)
            self.registro.scrivi(decisione.esito, "governatore", email_id=email.id,
                                 regola=decisione.regola, motivo=decisione.motivo, proposta=proposta)

            if decisione.esito == "consentita":
                self._esegui(proposta, esito)
            elif decisione.esito == "serve_approvazione":
                approvata = bool(self.approvatore(email, proposta))
                esito.approvazioni.append((proposta["strumento"], approvata))
                self.registro.scrivi("approvata" if approvata else "negata", "persona",
                                     email_id=email.id, proposta=proposta)
                if approvata:
                    self._esegui(proposta, esito)
            else:
                esito.bloccate.append((decisione.regola, decisione.motivo))

        if esito.bloccate:
            self._da_rivedere(esito, "Almeno un'azione è stata bloccata.")
        return esito

    def tratta_tutte(self) -> list[Esito]:
        esiti = []
        for email in self.casella.in_arrivo:
            if self.governatore.interruttore.attivo:
                self.registro.scrivi("arresto", "interruttore", motivo="Lavoro interrotto prima di questa email.",
                                     email_id=email.id)
                break
            esiti.append(self.tratta(email))
        return esiti
