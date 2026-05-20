# Aurum Data Crawler — Systemd Service Setup

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `UnifiedDataPipeline.run_end_of_day()` into a systemd oneshot service + timer that runs daily at 16:30 WIB (after IDX market close at 15:49 WIB).

**Architecture:** A thin Python runner script at `scripts/run_pipeline.py` calls the existing `UnifiedDataPipeline`. A `Type=oneshot` systemd service runs it. A systemd timer fires it daily at 09:30 UTC (16:30 WIB). This matches the homelab pattern already used by `nyx-indo-data`, `nyx-knowledge-ingestor`, etc.

**Tech Stack:** systemd, uv (project dep manager), `UnifiedDataPipeline` (already in `src/data_pipeline/unified_pipeline.py`), env from project `.env`.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `scripts/run_pipeline.py` | Create | Thin CLI runner: loads env, calls `run_end_of_day()`, exits 0/1 |
| `/etc/systemd/system/nyx-aurum-data.service` | Create | Oneshot systemd service |
| `/etc/systemd/system/nyx-aurum-data.timer` | Create | Daily timer at 09:30 UTC (16:30 WIB) |

---

## Task 1: Runner Script

**Files:**
- Create: `scripts/run_pipeline.py`
- Test: `tests/test_pipeline_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_runner.py
"""Smoke tests for the pipeline runner script."""
import importlib.util
import sys
from pathlib import Path


def test_runner_script_is_importable():
    """The runner script must be importable without side effects."""
    spec = importlib.util.spec_from_file_location(
        "run_pipeline",
        Path(__file__).parent.parent / "scripts" / "run_pipeline.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "main")


def test_runner_has_main_callable():
    spec = importlib.util.spec_from_file_location(
        "run_pipeline",
        Path(__file__).parent.parent / "scripts" / "run_pipeline.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
```

- [ ] **Step 2: Run test — expect FAIL** (file doesn't exist yet)

```bash
uv run pytest tests/test_pipeline_runner.py -v
```

Expected: `ModuleNotFoundError` or `FileNotFoundError`

- [ ] **Step 3: Create `scripts/` directory and runner script**

```python
# scripts/run_pipeline.py
"""
Runner script for the Aurum daily data pipeline.
Invoked by the nyx-aurum-data systemd service.

Exit codes:
  0 — pipeline completed successfully
  1 — pipeline failed (systemd will log the error)
"""
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Load project .env — keeps credentials out of the service unit
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from src.data_pipeline.unified_pipeline import UnifiedDataPipeline, PipelineRunConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("aurum-data-pipeline")


def main() -> int:
    logger.info("Aurum data pipeline starting")
    try:
        pipeline = UnifiedDataPipeline()
        pipeline.run_end_of_day(PipelineRunConfig())
        logger.info("Aurum data pipeline completed successfully")
        return 0
    except Exception as exc:
        logger.error("Aurum data pipeline FAILED: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

```bash
mkdir -p /home/vlain/workspaces/personal/project-aurum/scripts
```

- [ ] **Step 4: Run test — expect PASS**

```bash
uv run pytest tests/test_pipeline_runner.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Smoke-run the script (dry run — confirms imports, exits before DB)**

```bash
cd /home/vlain/workspaces/personal/project-aurum
uv run python -c "
import sys
sys.path.insert(0, '.')
from scripts.run_pipeline import main
print('Import OK — main callable:', callable(main))
"
```

Expected: `Import OK — main callable: True`

- [ ] **Step 6: Commit**

```bash
git add scripts/run_pipeline.py tests/test_pipeline_runner.py
git commit -m "feat: add pipeline runner script for systemd service [nyx-auto]"
```

---

## Task 2: Systemd Service Unit

**Files:**
- Create: `/etc/systemd/system/nyx-aurum-data.service`

The pattern used by all other nyx services: `Type=oneshot`, `EnvironmentFile` pointing to project `.env`, `WorkingDirectory` set to the project root, `ExecStart` using `uv run`.

- [ ] **Step 1: Write the service unit**

```ini
# /etc/systemd/system/nyx-aurum-data.service
[Unit]
Description=Aurum — daily IDX stock price + fundamentals + news pipeline
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=oneshot
User=vlain
Group=vlain
WorkingDirectory=/home/vlain/workspaces/personal/project-aurum
ExecStart=/home/vlain/.local/bin/uv run python scripts/run_pipeline.py
EnvironmentFile=/home/vlain/workspaces/personal/project-aurum/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nyx-aurum-data
TimeoutStartSec=1800
UMask=0022

[Install]
WantedBy=multi-user.target
```

```bash
sudo tee /etc/systemd/system/nyx-aurum-data.service << 'EOF'
[Unit]
Description=Aurum — daily IDX stock price + fundamentals + news pipeline
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=oneshot
User=vlain
Group=vlain
WorkingDirectory=/home/vlain/workspaces/personal/project-aurum
ExecStart=/home/vlain/.local/bin/uv run python scripts/run_pipeline.py
EnvironmentFile=/home/vlain/workspaces/personal/project-aurum/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nyx-aurum-data
TimeoutStartSec=1800
UMask=0022

[Install]
WantedBy=multi-user.target
EOF
```

- [ ] **Step 2: Verify systemd can parse it**

```bash
systemd-analyze verify /etc/systemd/system/nyx-aurum-data.service
```

Expected: no output (clean parse)

- [ ] **Step 3: Reload daemon and verify service is visible**

```bash
sudo systemctl daemon-reload
systemctl status nyx-aurum-data.service
```

Expected: `Loaded: loaded ... inactive (dead)`

---

## Task 3: Systemd Timer Unit

**Files:**
- Create: `/etc/systemd/system/nyx-aurum-data.timer`

IDX market closes 15:49 WIB. Run at 16:30 WIB = **09:30 UTC**.
`Persistent=true` ensures a missed run (e.g. server was off) fires on next boot.

- [ ] **Step 1: Write the timer unit**

```ini
# /etc/systemd/system/nyx-aurum-data.timer
[Unit]
Description=Aurum — daily data pipeline at 16:30 WIB (09:30 UTC)
Requires=nyx-aurum-data.service

[Timer]
OnCalendar=Mon..Fri *-*-* 09:30:00
RandomizedDelaySec=120
Persistent=true
AccuracySec=60s

[Install]
WantedBy=timers.target
```

```bash
sudo tee /etc/systemd/system/nyx-aurum-data.timer << 'EOF'
[Unit]
Description=Aurum — daily data pipeline at 16:30 WIB (09:30 UTC)
Requires=nyx-aurum-data.service

[Timer]
OnCalendar=Mon..Fri *-*-* 09:30:00
RandomizedDelaySec=120
Persistent=true
AccuracySec=60s

[Install]
WantedBy=timers.target
EOF
```

- [ ] **Step 2: Verify timer unit parses cleanly**

```bash
systemd-analyze verify /etc/systemd/system/nyx-aurum-data.timer
```

Expected: no output

- [ ] **Step 3: Enable and start the timer**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nyx-aurum-data.timer
```

- [ ] **Step 4: Confirm timer is active and shows next trigger**

```bash
systemctl list-timers nyx-aurum-data.timer
```

Expected: shows `nyx-aurum-data.timer` with next trigger around 09:30 UTC on the next weekday.

---

## Task 4: Manual Test Run

Verify the full chain works end-to-end before waiting for the timer.

- [ ] **Step 1: Trigger the service manually**

```bash
sudo systemctl start nyx-aurum-data.service
```

- [ ] **Step 2: Watch the journal in real time**

```bash
journalctl -u nyx-aurum-data -f
```

Expected output pattern:
```
nyx-aurum-data[XXXXX]: Aurum data pipeline starting
nyx-aurum-data[XXXXX]: Daily price fetch completed (job=...). Successful=N
nyx-aurum-data[XXXXX]: Aurum data pipeline completed successfully
systemd[1]: nyx-aurum-data.service: Deactivated successfully.
systemd[1]: Finished Aurum — daily IDX stock price + fundamentals + news pipeline.
```

- [ ] **Step 3: Verify service exited cleanly**

```bash
systemctl status nyx-aurum-data.service
```

Expected: `Active: inactive (dead)` with `status=0/SUCCESS`

- [ ] **Step 4: Commit notes if any adjustments were needed**

```bash
git add -A
git commit -m "chore: verify pipeline systemd service runs end-to-end [nyx-auto]"
```

---

## Verification Checklist

After all tasks complete:

```bash
# Timer is active
systemctl is-active nyx-aurum-data.timer   # → active

# Timer is enabled (survives reboot)
systemctl is-enabled nyx-aurum-data.timer  # → enabled

# Most recent run succeeded
journalctl -u nyx-aurum-data --since today --no-pager | tail -5

# Next trigger time
systemctl list-timers nyx-aurum-data.timer
```

## Notes

- `TimeoutStartSec=1800` gives the pipeline 30 minutes max — adjust if fundamentals ingestion is slow.
- `RandomizedDelaySec=120` staggers the run by up to 2 minutes to avoid hammering Yahoo Finance at exactly 09:30.
- The timer only fires Mon–Fri (`OnCalendar=Mon..Fri`). IDX is closed on Indonesian public holidays too, but those aren't handled here — the pipeline will simply fetch and find no new data on those days, which is harmless.
- If you need to backfill historical data: `sudo systemctl start nyx-aurum-data.service` after setting `BACKFILL_YEARS=2` env var, OR run directly: `uv run python scripts/run_pipeline.py --backfill 2` (requires adding argparse to the runner).
