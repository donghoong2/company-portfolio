"""scripts/*.py는 패키지가 아니라서 파일 경로로 불러온다."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def check_facts():
    return load("check_facts")


@pytest.fixture
def personal():
    return load("personal")
