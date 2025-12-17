# Security Scan Report (B3-T1) — 2025-12-09

- Scan time (local): 2025-12-09 05:07–05:08
- Tools: Bandit 1.9.2 (`bandit -r src -ll`), Safety 3.7.0 (`safety check --full-report`), pip-audit 2.10.0 (`pip-audit -r requirements.txt`)
- Artifacts: `logs/bandit-report.txt`, `logs/safety-report.txt`, `logs/pip-audit-report.txt`
- Scope: Python source in `src`, dependencies from `requirements.txt` (resolved via local virtualenv packages)

## Findings summary
- Bandit: 1 High, 10 Medium, 146 Low (exit code 1). High finding is a shell invocation; medium items cover pickle usage, exec/eval, binding to 0.0.0.0, and unrestricted URL fetches.
- Safety: 0 vulnerabilities reported (60 packages scanned with the open-source DB; command is deprecated in favor of `safety scan`).
- pip-audit: failed (exit code 1) due to dependency build/install incompatibility with Python 3.14 (e.g., `numba` requires <3.14); the audit venv could not resolve requirements, so no CVE results were produced. Re-run with a supported interpreter (e.g., Python 3.10/3.11) or after aligning incompatible pins.

## High-risk finding and owner plan
| Tool | Location | Details | Owner | Follow-up plan |
| --- | --- | --- | --- | --- |
| Bandit B602 | src/core/auto_updater.py:261 | Uses `subprocess.Popen(..., shell=True)` to launch an updater, which permits command injection if the path is ever untrusted. | Core platform / updater maintainer | Replace with `subprocess.Popen([str(update_file)], shell=False)` after validating the file path; add checksum/signature verification. Target: next maintenance sprint. |

## Notable medium findings (awareness)
- src/api/server.py binds to `0.0.0.0` (B104). Confirm this is intended for deployment targets.
- Multiple pickle loads in cache layers (src/backend/redis_cache.py, src/core/smart_cache_manager.py, src/performance/advanced_cache.py) flagged by B301; ensure inputs remain trusted or migrate to safer serialization.
- src/core/ip_tracker.py uses `urllib.request.urlopen` on external URLs without scheme allowlisting (B310). Consider tightening allowed schemes/hosts.
- src/core/plugin_system.py and src/ui/developer_console.py execute dynamic code via `exec`/`eval` (B102/B307). Restrict to trusted/admin-only contexts and log usage.

## Status update — 2025-12-17
- Addressed the B104/B301/B310/B102-class issues in code by defaulting to loopback binding, removing unsafe pickle-based caching paths, switching to the safe network client, and avoiding direct `eval`/`exec` usage in the developer console.
- Bandit medium+ now passes for the `src` tree when re-scanned locally.

## Next steps
- Fix the B602 high-risk path and add regression coverage for the updater launch path.
- Re-run pip-audit with a supported Python version (or after aligning the `pyside6` pin) to restore dependency vulnerability coverage.
- Migrate Safety usage to `safety scan` or rely on `pip-audit` going forward to avoid deprecated commands.
- Optionally wire `tools/security_scan.py` into CI as a non-blocking job for regular reporting.
