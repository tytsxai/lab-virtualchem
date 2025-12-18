# Quick Start

This short guide mirrors the canonical documentation and keeps the minimal, repeatable steps in one place.

## Prerequisites

- Python 3.11 (virtual environment strongly recommended)
- Access to `requirements.lock` (or `requirements.txt` when regenerating the lock file)
- Git and a shell with `python3.11` on the `PATH`

## Setup Steps

1. Create and activate the virtual environment, then install dependencies:
   ```bash
   python3.11 -m venv venv311
   venv311/bin/python -m pip install -r requirements.lock
   # Need to refresh dependencies? use requirements.txt instead.
   ```
2. Copy the sample environment file, then run the configuration validator
   to ensure key directories exist:
   ```bash
   cp env.example .env
   venv311/bin/python tools/validate_config.py
   ```
3. Launch the application in development mode:
   ```bash
   venv311/bin/python main.py --env development
   ```
4. Run the automated tests to verify your setup:
   ```bash
   venv311/bin/python -m pytest -q
   ```
   If you are running in a headless environment and Qt crashes, retry with:
   `QT_QPA_PLATFORM=offscreen venv311/bin/python -m pytest -q` (or use `make test-fast`).

## Next Steps

- `QUICK_START_GUIDE.md`: Detailed onboarding with screenshots and feature highlights.
- `README.md`: Full project overview plus extended usage instructions.
- `QUICK_START_COMPLETION.md`: Post-setup checklist to confirm production readiness.
