from pathlib import Path
import tomllib


def _load_project_metadata():
    project_root = Path(__file__).resolve().parents[3]
    pyproject_path = project_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)["project"]


_project = _load_project_metadata()

PIPELINE_NAME = _project["name"]
PIPELINE_VERSION = _project["version"]