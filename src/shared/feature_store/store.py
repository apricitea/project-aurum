"""
Lightweight feature store abstraction for Project Aurum.
Supports segregated storage for ML, LLM agent, and AMT workloads using Parquet artifacts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureStoreConfig:
    root_path: Path
    categories: Iterable[str] = ("ml", "llm", "amt")
    use_delta_format: bool = False  # Hook for future upgrades


@dataclass
class FeatureStoreDataset:
    name: str
    category: str
    version: str
    path: Path
    created_at: datetime
    metadata: Dict


class FeatureStore:
    """
    Minimal feature store built on top of Parquet flat files.
    Provides dataset versioning, metadata tracking, and consistent layout.
    """

    def __init__(self, config: FeatureStoreConfig) -> None:
        self.config = config
        self.root_path = config.root_path
        self.root_path.mkdir(parents=True, exist_ok=True)
        for category in config.categories:
            (self.root_path / category).mkdir(exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def write_dataset(
        self,
        *,
        name: str,
        category: str,
        frame: pd.DataFrame,
        metadata: Optional[Dict] = None,
        overwrite: bool = False,
    ) -> FeatureStoreDataset:
        self._validate_category(category)
        version = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dataset_path = self._dataset_path(name, category, version)
        dataset_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            frame.to_parquet(dataset_path, index=False)
        except Exception as exc:
            logger.warning("Parquet write failed (%s). Falling back to CSV for %s/%s", exc, category, name)
            dataset_path = dataset_path.with_suffix(".csv")
            frame.to_csv(dataset_path, index=False)

        manifest = self._manifest_path(name, category)
        entry = {
            "name": name,
            "category": category,
            "version": version,
            "path": str(dataset_path.relative_to(self.root_path)),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        if overwrite:
            history = [entry]
        else:
            history = self._load_manifest(manifest)
            history.insert(0, entry)

        self._save_manifest(manifest, history)
        logger.info("Feature dataset written: %s (%s)", name, version)
        return FeatureStoreDataset(
            name=name,
            category=category,
            version=version,
            path=dataset_path,
            created_at=datetime.fromisoformat(entry["created_at"]),
            metadata=entry["metadata"],
        )

    def read_latest(
        self,
        *,
        name: str,
        category: str,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        dataset = self.latest_dataset(name=name, category=category)
        if not dataset:
            raise FileNotFoundError(f"No dataset available for {category}/{name}")
        return pd.read_parquet(dataset.path, columns=columns)

    def latest_dataset(self, *, name: str, category: str) -> Optional[FeatureStoreDataset]:
        self._validate_category(category)
        history = self._load_manifest(self._manifest_path(name, category))
        if not history:
            return None
        entry = history[0]
        return FeatureStoreDataset(
            name=entry["name"],
            category=entry["category"],
            version=entry["version"],
            path=self.root_path / entry["path"],
            created_at=datetime.fromisoformat(entry["created_at"]),
            metadata=entry["metadata"],
        )

    def list_datasets(self, category: Optional[str] = None) -> List[FeatureStoreDataset]:
        datasets: List[FeatureStoreDataset] = []
        categories = [category] if category else list(self.config.categories)
        for cat in categories:
            manifests = (self.root_path / cat).glob("*.manifest.json")
            for manifest in manifests:
                history = self._load_manifest(manifest)
                if not history:
                    continue
                entry = history[0]
                datasets.append(
                    FeatureStoreDataset(
                        name=entry["name"],
                        category=entry["category"],
                        version=entry["version"],
                        path=self.root_path / entry["path"],
                        created_at=datetime.fromisoformat(entry["created_at"]),
                        metadata=entry["metadata"],
                    )
                )
        return datasets

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #

    def _validate_category(self, category: str) -> None:
        if category not in self.config.categories:
            raise ValueError(f"Unknown feature category '{category}'. Expected one of {self.config.categories}")

    def _dataset_path(self, name: str, category: str, version: str) -> Path:
        filename = f"{name}-{version}.parquet"
        return self.root_path / category / name / filename

    def _manifest_path(self, name: str, category: str) -> Path:
        filename = f"{name}.manifest.json"
        return self.root_path / category / filename

    @staticmethod
    def _load_manifest(path: Path) -> List[Dict]:
        if not path.exists():
            return []
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _save_manifest(path: Path, history: List[Dict]) -> None:
        path.write_text(json.dumps(history, indent=2))
