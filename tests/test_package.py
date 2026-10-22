import re
from pathlib import Path

import FCB1010

PACKAGE = Path(FCB1010.__file__).parent


def test_package_imports_without_live() -> None:
    assert callable(FCB1010.create_instance)


def test_only_live_adapter_imports_live() -> None:
    pattern = re.compile(r"^\s*(import|from)\s+(Live|_Framework|ableton)\b", re.MULTILINE)
    offenders = [
        p.name
        for p in PACKAGE.glob("*.py")
        if p.name != "live_adapter.py" and pattern.search(p.read_text())
    ]
    assert offenders == []
