import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from antincendio_app.gestionale import main
sys.exit(main("--silenzioso" in sys.argv))
