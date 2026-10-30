import os
from pathlib import Path

EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "/app/exports"))
