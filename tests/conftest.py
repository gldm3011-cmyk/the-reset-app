import os, sys, tempfile
from pathlib import Path
# Base temporal y configuración de prueba: las pruebas nunca tocan una base real
os.environ["THE_RESET_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["ADMIN_EMAIL"] = "admin@prueba.co"
os.environ["ADMIN_PASSWORD"] = "AdminPrueba1"
os.environ["THE_RESET_DEMO"] = "1"          # carga profesionales y cuentas de ejemplo (clave Demo12345) para las pruebas de interfaz
os.environ.pop("DATABASE_URL", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
