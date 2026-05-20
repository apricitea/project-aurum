"""Tests that the FastAPI app can be imported and health endpoints work."""


def test_app_imports_without_error():
    """App module must import without NameError (e.g. missing Request import)."""
    import importlib
    mod = importlib.import_module("src.api.main")
    assert hasattr(mod, "app")


def test_health_endpoint_exists():
    from src.api.main import app
    routes = {route.path for route in app.routes}
    assert "/health" in routes
    assert "/health/detailed" in routes


def test_celery_app_exported():
    """celery_app must be importable from src.api.main (Celery worker entry point)."""
    from src.api.main import celery_app
    assert celery_app is not None
    assert celery_app.main == "project_aurum"
