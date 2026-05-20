"""Smoke tests for the pipeline runner script."""
import importlib.util
from pathlib import Path


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_pipeline",
        Path(__file__).parent.parent / "scripts" / "run_pipeline.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_runner_script_is_importable():
    """The runner script must be importable without side effects."""
    mod = _load_runner()
    assert hasattr(mod, "main")


def test_runner_has_main_callable():
    mod = _load_runner()
    assert callable(mod.main)
