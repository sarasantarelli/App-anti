#!/usr/bin/env bash
# macOS / Linux: crea l'ambiente al primo avvio e lancia l'app
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; fi
.venv/bin/python -m antincendio_app diagnostica || true
.venv/bin/python -m antincendio_app serve
