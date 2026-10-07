from antincendio_app import regole as R


def test_rvita_espansione_e_generico():
    assert R.expand_rvita("Cii1–Cii3, A1") == {"Cii1", "Cii2", "Cii3", "A1"}
    assert R.rvita_in("Ciii2", {"C2"})
    assert not R.rvita_in("B2", {"A1", "A2"})


def test_matrice_g3_ammessi():
    assert R.rvita_ammesso("A", 4) and not R.rvita_ammesso("B", 4) and not R.rvita_ammesso("D", 3)


def test_qfd_e_classe_rei():
    assert R.delta_q1(499) == 1.0 and R.delta_q1(500) == 1.2 and R.delta_q1(10000) == 2.0
    assert R.classe_rei(200) == "Nessun requisito" and R.classe_rei(201) == 15 and R.classe_rei(900) == 60 and R.classe_rei(2500) == 240


def test_esodo():
    assert R.uscite_minime(501, "A2", 0.1) == 3 and R.uscite_minime(60, "A2", 0.1) == 2 and R.uscite_minime(10, "A2", 0.1) == 1
    assert R.largh_min_assoluta(300) == 900 and R.largh_min_assoluta(301) == 1000 and R.largh_min_assoluta(1001) == 1200
    assert R.LES["A2"] == 60 and R.LCC["B2"] == (50, 20) and R.lu_oriz("Ciii2") == 4.10
    assert R.lu_vert("A2", 2) == 4.00


def test_estintori_e_formazione():
    assert R.estintori_a("A2", 100)["cap_A"] == 13 and R.estintori_a("B2", 100)["cap_A"] == 21 and R.estintori_a("A4", 100)["cap_A"] == 27
    assert R.estintori_b(60)["cap_B"] == 89 and R.estintori_b(250)["cap_B"] == 233
    assert R.formazione(True, 20)["livello"] == 1 and R.formazione(False, 20)["livello"] == 2 and R.formazione(False, 400)["livello"] == 3


def test_screening_dpr151():
    r = R.screening_dpr151({"occupanti": 60, "superficie": 450, "tipologie": ["commercio"]})
    assert r[0]["voce"] == 69 and r[0]["esito"] == "SOPRA"
    r = R.screening_dpr151({"occupanti": 60, "superficie": 350, "tipologie": ["commercio"]})
    assert r[0]["esito"] == "sotto"
