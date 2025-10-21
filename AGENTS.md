# Repository Guidelines

## Project Structure & Modules
- `custom_components/android_tv_box/`: Integration code (entry `__init__.py`, config UI `config_flow.py`, data `coordinator.py`, ADB utilities `adb_manager.py`, entities: `media_player.py`, `sensor.py`, `switch.py`, `button.py`, `select.py`, `number.py`, `camera.py`, shared `const.py`).
- `custom_components/android_tv_box/translations/`: UI strings.
- Root: `README.md`, `info.md`, `hacs.json`, `requirements.txt`, `VERSION`, `.github/`.

## Build, Test, and Development
- Create venv and install deps:
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Link into a Home Assistant config for local testing:
  - `ln -s $(pwd)/custom_components/android_tv_box /config/custom_components/android_tv_box`
  - Restart Home Assistant and add the integration via UI.
- Optional tooling (recommended locally):
  - Format: `black custom_components`
  - Lint: `ruff check custom_components`
  - Tests (if added): `pytest -q`

## Coding Style & Naming
- Python 3.11+, PEP 8, 4‑space indent, type hints.
- Modules/functions: `snake_case`; classes: `PascalCase`; constants in `const.py` as `UPPER_SNAKE_CASE`.
- Follow Home Assistant async patterns (prefer `async_` APIs, avoid blocking I/O on event loop).
- Entity IDs/names: `android_tv_box_*` prefix; keep attributes minimal and documented.

## Testing Guidelines
- Framework: `pytest` with `pytest-homeassistant-custom-component`.
- Place tests under `tests/`; files named `test_*.py`; mirror module layout (e.g., `test_media_player.py`).
- Aim for ≥80% coverage on new/changed code; mock ADB interactions.
- Run: `pytest -q` (add `-k` to filter).

## Commit & Pull Requests
- Commits: imperative, scoped; prefer Conventional Commits (e.g., `feat(media_player): add cast url`) when feasible.
- PRs must include: summary, rationale, screenshots/logs for UI/device changes, linked issue, and testing notes.
- Versioning: bump `manifest.json` `version` and root `VERSION` when user‑visible behavior changes; update `strings.json` and translations as needed.

## Security & Configuration
- Do not commit device IPs, ADB keys, or secrets. Use examples/placeholders.
- Keep network ADB exposed only on trusted networks; document any required ports in README.
