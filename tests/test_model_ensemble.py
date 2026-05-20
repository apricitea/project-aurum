"""Smoke tests for model_ensemble module."""
import warnings
import importlib


def test_model_ensemble_imports():
    """Module must import without error."""
    mod = importlib.import_module(
        "src.domains.trading.infrastructure.ml_models.model_ensemble"
    )
    assert hasattr(mod, "IDXQuantitativeModel")


def test_idx_quantitative_model_instantiates():
    from src.domains.trading.infrastructure.ml_models.model_ensemble import IDXQuantitativeModel
    model = IDXQuantitativeModel()
    assert model.is_trained is False
    assert model.technical_model is not None
    assert model.fundamental_model is not None
    assert model.sentiment_model is not None
    assert model.meta_model is not None


def test_no_pandas_deprecation_on_import():
    """No FutureWarning from pandas on module import."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        importlib.reload(
            importlib.import_module(
                "src.domains.trading.infrastructure.ml_models.model_ensemble"
            )
        )
