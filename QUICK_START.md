# Quick Start

This short checklist points to the canonical docs shipped with the project.

1. Install the Python 3.11 virtual environment and project dependencies:
   ```bash
   python3.11 -m venv venv311
   venv311/bin/python -m pip install -r requirements.txt
   ```
2. Review `QUICK_START_GUIDE.md` for the detailed walkthrough and
   `QUICK_START_COMPLETION.md` for the follow-up checklist.
3. Launch the application in development mode:
   ```bash
   venv311/bin/python main.py --env development
   ```
4. Run the automated tests to verify your setup:
   ```bash
   venv311/bin/python -m pytest -q
   ```

These steps mirror the more complete instructions but keep the bare minimum in one place.
