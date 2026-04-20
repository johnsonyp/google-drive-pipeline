from pathlib import Path

# General
ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = Path(__file__).resolve().parents[1]

# Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]