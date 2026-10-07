"""Modello dati del caso. Ogni dato porta la propria fonte (tracciabilità per l'organo di vigilanza)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Dato:
    valore: Any = None
    fonte: str = "non rilevato"      # nome file / "inserito dal tecnico" / "default cautelativo"
    confermato: bool = False         # True = validato dal tecnico

    def ok(self) -> bool:
        return self.valore not in (None, "", [])


@dataclass
class Finding:
    """Esito di un agente: rilievo, incongruenza, dato mancante, non conformità."""
    agente: str
    livello: str          # info | attenzione | critico
    messaggio: str
    riferimento: str = ""  # citazione normativa


@dataclass
class Caso:
    dati: dict[str, Dato] = field(default_factory=dict)
    evidenze: list[dict] = field(default_factory=list)   # estratti dai documenti (file, tipo, testo)
    findings: list[Finding] = field(default_factory=list)
    esito: dict[str, Any] = field(default_factory=dict)   # risultati degli agenti
    log: list[str] = field(default_factory=list)

    def set(self, k, v, fonte="inserito dal tecnico", confermato=True):
        self.dati[k] = Dato(v, fonte, confermato)

    def get(self, k, default=None):
        d = self.dati.get(k)
        return d.valore if d and d.ok() else default

    def add(self, agente, livello, msg, rif=""):
        self.findings.append(Finding(agente, livello, msg, rif))

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Caso":
        c = Caso()
        c.dati = {k: Dato(**v) for k, v in d.get("dati", {}).items()}
        c.evidenze = d.get("evidenze", [])
        c.findings = [Finding(**f) for f in d.get("findings", [])]
        c.esito = d.get("esito", {})
        c.log = d.get("log", [])
        return c
