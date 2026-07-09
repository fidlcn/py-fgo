"""Application configuration loaded from configs/default.yaml.

Missing values fall back to the spec defaults (section 12). The config is a
plain dataclass tree so the worker and API can read it without depending on
the YAML source.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Tuple

import yaml

# Root of the repository: backend/core/config.py -> up three levels.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "default.yaml"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "app.db"
DEFAULT_LOG_DIR = REPO_ROOT / "logs"
DEFAULT_SCREENSHOT_DIR = DEFAULT_LOG_DIR / "screenshots"
DEFAULT_TEMPLATE_DIR = REPO_ROOT / "assets" / "templates"


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    lan_enabled: bool = False
    auth_enabled: bool = True
    auth_token: str = "change-me"


@dataclass
class AdbConfig:
    path: str = "adb"
    command_timeout_seconds: float = 10.0


@dataclass
class RuntimeConfig:
    base_resolution: Tuple[int, int] = (1280, 720)
    screenshot_interval_ms: int = 700
    action_delay_ms: int = 350
    max_instances: int = 4
    save_normal_screenshots: bool = False
    keep_recent_screenshots: int = 20


@dataclass
class VisionConfig:
    template_threshold: float = 0.82
    state_threshold: float = 0.85
    use_ocr: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    screenshot_on_error: bool = True


@dataclass
class FgoConfig:
    package_names: tuple[str, ...] = (
        "com.bilibili.fatego",
        "com.aniplex.fategrandorder",
        "com.aniplex.fategrandorder.en",
    )


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    adb: AdbConfig = field(default_factory=AdbConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    fgo: FgoConfig = field(default_factory=FgoConfig)

    # Paths resolved relative to the repo root.
    db_path: Path = field(default_factory=lambda: DEFAULT_DB_PATH)
    log_dir: Path = field(default_factory=lambda: DEFAULT_LOG_DIR)
    screenshot_dir: Path = field(default_factory=lambda: DEFAULT_SCREENSHOT_DIR)
    template_dir: Path = field(default_factory=lambda: DEFAULT_TEMPLATE_DIR)

    @classmethod
    def default(cls) -> "AppConfig":
        return cls()

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AppConfig":
        """Load config from YAML, overlaying spec defaults.

        If the file does not exist, the spec defaults are returned unchanged.
        """
        config = cls.default()
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not cfg_path.exists():
            return config
        with cfg_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        _apply_section(config.server, raw.get("server", {}))
        _apply_section(config.adb, raw.get("adb", {}))
        _apply_section(config.runtime, raw.get("runtime", {}), casts={"base_resolution": tuple})
        _apply_section(config.vision, raw.get("vision", {}))
        _apply_section(config.logging, raw.get("logging", {}))
        _apply_section(config.fgo, raw.get("fgo", {}), casts={"package_names": tuple})
        return config

    def ensure_dirs(self) -> None:
        """Create runtime directories if they are missing."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)


def _apply_section(instance: Any, data: dict, casts: dict[str, Any] | None = None) -> None:
    """Copy known keys from ``data`` onto the dataclass ``instance``."""
    casts = casts or {}
    if not is_dataclass(instance):
        return
    valid = {f.name for f in fields(instance)}
    for key, value in (data or {}).items():
        if key in valid and value is not None:
            setattr(instance, key, casts.get(key, lambda v: v)(value))
