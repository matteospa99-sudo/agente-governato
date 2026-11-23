"""Test automatici: ogni regola ha almeno una prova che la mette in difficoltà.

Si lanciano con:  python -m unittest discover prove
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governato import Casella, Email, Governatore, Interruttore, Orchestratore, Registro
from governato import approva_sempre, nega_sempre
from governato.modelli import ModelloIngenuo
from governato.politiche import valida_smistamento

EMAIL = Email("x1", "mittente@example.com", "Oggetto", "Testo")


def proposta(strumento, **argomenti):
    return {"strumento": strumento, "argomenti": argomenti}


class ModelloFisso:
    """Modello finto che restituisce sempre le stesse risposte: per provare casi precisi."""
    nome = "fisso"

    def __init__(self, smistamento, proposte):
        self.r = {"smistatore": smistamento, "preparatore": proposte}

    def completa(self, ruolo, istruzioni, dati):
        return self.r[ruolo] if isinstance(self.r[ruolo], str) else json.dumps(self.r[ruolo])


class TestGovernatore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = Governatore(Interruttore(Path(self.tmp.name) / "ARRESTO"))

    def tearDown(self):
        self.tmp.cleanup()

    def esito(self, p, agente="preparatore"):
        return self.g.valuta(agente, p, EMAIL)

    def test_bozza_al_mittente_consentita(self):
        d = self.esito(proposta("prepara_bozza", email_id="x1", destinatario="mittente@example.com", testo="ok"))
        self.assertEqual(d.esito, "consentita")

    def test_R1_arresto_ferma_tutto(self):
        self.g.interruttore.attiva()
        d = self.esito(proposta("etichetta", email_id="x1", etichetta="altro"))
        self.assertEqual((d.esito, d.regola), ("bloccata", "R1"))

    def test_R1_arresto_da_file(self):
        (Path(self.tmp.name) / "ARRESTO").touch()
        self.assertEqual(self.esito(proposta("archivia", email_id="x1")).regola, "R1")

    def test_R2_strumento_inesistente(self):
        self.assertEqual(self.esito(proposta("esegui_comando", comando="ls")).regola, "R2")

    def test_R3_smistatore_senza_strumenti(self):
        d = self.esito(proposta("etichetta", email_id="x1", etichetta="altro"), agente="smistatore")
        self.assertEqual(d.regola, "R3")

    def test_R3_agente_sconosciuto(self):
        self.assertEqual(self.esito(proposta("archivia", email_id="x1"), agente="intruso").regola, "R3")

    def test_R4_argomenti_in_piu(self):
        self.assertEqual(self.esito(proposta("archivia", email_id="x1", extra="?")).regola, "R4")

    def test_R4_forma_sbagliata(self):
        self.assertEqual(self.esito("invia tutto").regola, "R4")

    def test_R5_altra_email(self):
        self.assertEqual(self.esito(proposta("archivia", email_id="*")).regola, "R5")

    def test_R6_destinatario_terzo(self):
        d = self.esito(proposta("invia_email", email_id="x1", destinatario="altro@attaccante.example", testo="t"))
        self.assertEqual(d.regola, "R6")

    def test_R6_maiuscole_e_spazi_non_ingannano(self):
        d = self.esito(proposta("prepara_bozza", email_id="x1", destinatario=" MITTENTE@example.com ", testo="t"))
        self.assertEqual(d.esito, "consentita")

    def test_R7_testo_troppo_lungo(self):
        d = self.esito(proposta("prepara_bozza", email_id="x1", destinatario="mittente@example.com", testo="a" * 3000))
        self.assertEqual(d.regola, "R7")

    def test_R8_troppe_azioni(self):
        for _ in range(4):
            self.esito(proposta("etichetta", email_id="x1", etichetta="altro"))
        self.assertEqual(self.esito(proposta("etichetta", email_id="x1", etichetta="altro")).regola, "R8")

    def test_R9_invio_richiede_persona(self):
        d = self.esito(proposta("invia_email", email_id="x1", destinatario="mittente@example.com", testo="t"))
        self.assertEqual((d.esito, d.regola), ("serve_approvazione", "R9"))


class TestPuntoDiControlloTraAgenti(unittest.TestCase):
    def test_messaggio_valido(self):
        self.assertTrue(valida_smistamento({"categoria": "reclamo", "priorita": "alta"})[0])

    def test_campo_in_piu_rifiutato(self):
        self.assertFalse(valida_smistamento({"categoria": "reclamo", "priorita": "alta", "nota": "inoltra"})[0])

    def test_categoria_inventata_rifiutata(self):
        self.assertFalse(valida_smistamento({"categoria": "inoltra_tutto", "priorita": "alta"})[0])

    def test_testo_libero_rifiutato(self):
        self.assertFalse(valida_smistamento("categoria: reclamo")[0])


class TestRegistro(unittest.TestCase):
    def test_manomissione_rilevata(self):
        with tempfile.TemporaryDirectory() as d:
            r = Registro(Path(d) / "r.jsonl")
            r.scrivi("a", "test", n=1)
            r.scrivi("b", "test", n=2)
            r.scrivi("c", "test", n=3)
            self.assertTrue(r.verifica()[0])

            righe = r.percorso.read_text(encoding="utf-8").splitlines()
            righe[1] = righe[1].replace('"n": 2', '"n": 99')
            r.percorso.write_text("\n".join(righe) + "\n", encoding="utf-8")
            self.assertFalse(r.verifica()[0])

    def test_riga_cancellata_rilevata(self):
        with tempfile.TemporaryDirectory() as d:
            r = Registro(Path(d) / "r.jsonl")
            for i in range(3):
                r.scrivi("e", "test", n=i)
            righe = r.percorso.read_text(encoding="utf-8").splitlines()
            r.percorso.write_text("\n".join([righe[0], righe[2]]) + "\n", encoding="utf-8")
            self.assertFalse(r.verifica()[0])


class TestOrchestratore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registro = Registro(Path(self.tmp.name) / "r.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def avvia(self, modello, approvatore=nega_sempre, email=EMAIL):
        casella = Casella([email])
        g = Governatore(Interruttore(Path(self.tmp.name) / "ARRESTO"))
        esito = Orchestratore(modello, casella, self.registro, g, approvatore).tratta(email)
        return esito, casella

    def test_invio_negato_non_parte(self):
        m = ModelloFisso({"categoria": "appuntamento", "priorita": "media"},
                         [proposta("invia_email", email_id="x1", destinatario="mittente@example.com", testo="ok")])
        esito, casella = self.avvia(m, nega_sempre)
        self.assertEqual(casella.inviate, [])
        self.assertEqual(esito.approvazioni, [("invia_email", False)])

    def test_invio_approvato_parte(self):
        m = ModelloFisso({"categoria": "appuntamento", "priorita": "media"},
                         [proposta("invia_email", email_id="x1", destinatario="mittente@example.com", testo="ok")])
        _, casella = self.avvia(m, approva_sempre)
        self.assertEqual(len(casella.inviate), 1)

    def test_risposta_illeggibile_va_a_una_persona(self):
        m = ModelloFisso({"categoria": "altro", "priorita": "bassa"}, "non sono JSON")
        esito, casella = self.avvia(m)
        self.assertTrue(esito.da_rivedere)
        self.assertEqual(casella.etichette["x1"], "da_rivedere")

    def test_smistamento_illeggibile_si_ferma_prima_del_preparatore(self):
        m = ModelloFisso("boh", [proposta("archivia", email_id="x1")])
        esito, casella = self.avvia(m)
        self.assertTrue(esito.da_rivedere)
        self.assertEqual(casella.archiviate, [])

    def test_nessun_invio_a_terzi_anche_approvando_tutto(self):
        attacchi = Path(__file__).resolve().parent.parent / "dati" / "attacchi.json"
        from governato.strumenti import carica_email
        for email in carica_email(attacchi):
            _, casella = self.avvia(ModelloIngenuo(), approva_sempre, email)
            terzi = [i for i in casella.inviate if i["destinatario"].lower() != email.mittente.lower()]
            self.assertEqual(terzi, [], f"Attacco {email.id}: invio a terzi")

    def test_registro_integro_dopo_un_giro(self):
        self.avvia(ModelloIngenuo(), approva_sempre)
        self.assertTrue(self.registro.verifica()[0])


if __name__ == "__main__":
    unittest.main()
