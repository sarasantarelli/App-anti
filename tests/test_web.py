import os, tempfile
os.environ["APP_DATA_DIR"] = tempfile.mkdtemp()
os.environ["APP_PASSWORD"] = "segreta"
from fastapi.testclient import TestClient
from antincendio_app.web import server

c = TestClient(server.app)
AUTH = ("u", "segreta")


def test_auth_richiesta():
    assert c.get("/api/schema").status_code == 401
    assert c.get("/api/health").status_code == 200
    assert c.get("/", auth=("u", "no")).status_code == 401


def test_flusso_completo():
    j = c.post("/api/pratiche", auth=AUTH).json()
    pid = j["id"]
    assert j["sintesi"]["stato"] == "BOZZA" and j["domande"]
    j = c.put(f"/api/pratiche/{pid}/dati", auth=AUTH, json={"ragione_sociale": "X Srl", "superficie_mq": "200", "quota_min": 0, "quota_max": 3,
              "occupanti_lavoratori": 4, "tipologia_attivita": ["ufficio"], "sostanze_significative": False, "lavorazioni_pericolose": False, "aperta_pubblico": False}).json()
    assert j["sintesi"]["template"] == "minicodice"
    vid = j["voci"][0]["id"]
    j = c.put(f"/api/pratiche/{pid}/risposte", auth=AUTH, json={vid: {"esito": "NC", "azione": "Fare Y"}}).json()
    assert j["azioni"][0]["azione"] == "Fare Y"
    g = c.post(f"/api/pratiche/{pid}/genera?pdf=false", auth=AUTH).json()
    assert g["zip"] and g["documenti"][0]["file"].endswith(".docx")
    r = c.get(f"/api/pratiche/{pid}/download/{g['zip']}", auth=AUTH)
    assert r.status_code == 200 and r.content[:2] == b"PK"
    assert c.get("/api/pratiche/zzzz", auth=AUTH).status_code == 404
    assert c.get(f"/api/pratiche/{pid}/download/..%2Fcaso.json", auth=AUTH).status_code in (404, 422)
