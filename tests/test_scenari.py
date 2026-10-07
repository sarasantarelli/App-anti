import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import sweep


def test_giro_di_prove_senza_anomalie():
    assert sweep.main(8, 3) == 0


def test_ristorante_con_eventi_e_discriminanti(tmp_path):
    from antincendio_app.coordinatore import esegui_tutto
    base = dict(ragione_sociale="Locale X", indirizzo="Via 1", datore_lavoro="A", rspp="B", superficie_mq=150, quota_min=0, quota_max=3, occupanti_lavoratori=4,
                occupanti_terzi=40, tipologia_attivita=["ristorazione"], aperta_pubblico=True, sostanze_significative=False, lavorazioni_pericolose=False, qf_mj_m2=300)
    c, _ = esegui_tutto(dict(base, eventi_intrattenimento=True), [], tmp_path / "a", pdf=False)
    assert c.esito["normativo"]["soggetta_dpr151"] is False        # musica senza discriminanti: esclusa (V.15.1 c.2 lett. b)
    c, _ = esegui_tutto(dict(base, eventi_intrattenimento=True, pista_ballo=True), [], tmp_path / "b", pdf=False)
    assert c.esito["normativo"]["soggetta_dpr151"] is True          # pista da ballo: n. 65
    c, _ = esegui_tutto(dict(base, eventi_intrattenimento=True, pista_ballo=True, eventi_solo_aperto=True), [], tmp_path / "c", pdf=False)
    assert c.esito["normativo"]["soggetta_dpr151"] is False         # manifestazioni temporanee all'aperto: escluse


def test_piu_destinazioni_governa_il_profilo_piu_elevato(tmp_path):
    from antincendio_app.coordinatore import esegui_tutto
    d = dict(ragione_sociale="Hotel Y", indirizzo="Via 2", datore_lavoro="A", rspp="B", superficie_mq=500, quota_min=0, quota_max=8, occupanti_lavoratori=6,
             occupanti_terzi=20, tipologia_attivita=["ufficio"], aperta_pubblico=True, sostanze_significative=False, lavorazioni_pericolose=False, qf_mj_m2=300,
             locali=[{"nome": "Uffici", "mq": 200, "tipo": "ufficio"}, {"nome": "Camere", "mq": 300, "tipo": "ricettivo"}])
    c, _ = esegui_tutto(d, [], tmp_path, pdf=False)
    assert c.esito["rischio"]["rvita"].startswith("Ciii")
    assert {x["nome"] for x in c.esito["rischio"]["rvita_locali"]} == {"Uffici", "Camere"}


def test_minicodice_usa_valori_fissi(tmp_path):
    from antincendio_app.coordinatore import esegui_tutto
    d = dict(ragione_sociale="Z", indirizzo="V", datore_lavoro="A", rspp="B", superficie_mq=180, quota_min=0, quota_max=3, occupanti_lavoratori=8,
             tipologia_attivita=["ufficio"], sostanze_significative=False, lavorazioni_pericolose=False, qf_mj_m2=300)
    c, _ = esegui_tutto(d, [], tmp_path, pdf=False)
    dim = c.esito["dimensionamento"]
    assert dim["modo"] == "minicodice" and dim["les_max"] == 60 and dim["lcc_max"] == 15 and dim["uscite_min"] == 2   # sup > 150 m²
