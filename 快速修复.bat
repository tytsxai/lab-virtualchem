@echo off
echo Running lint and targeted tests...
python -m pip install -r requirements-dev.txt >NUL 2>&1
echo Running pytest -k quick
python -m pytest -k quick
