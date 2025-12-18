# Configuration hardening

- Secrets load from environment variables by default. For desktop packaged builds (`sys.frozen`), the app will generate per-machine secrets on first start and persist them under the user runtime directory (e.g. `~/.virtualchemlab/config.json`, or via `VCL_DATA_DIR` / `VCL_CONFIG_PATH`). Enterprise deployments can still override secrets via environment variables. `VCL_ADMIN_SECRET_KEY` is required when starting the Admin API (`src/api/admin_api.py`) and is validated there (including a minimum length check).
- Configuration precedence: environment variables override `config/*.json` and `config.json`. Non-production can fall back to generated placeholders for local runs, but production never accepts file-stored secrets.
- Developer/debug defaults: production sets `app.debug=false` and `developer.enabled=false`. To explicitly enable developer mode, set `DEVELOPER_MODE_ENABLED=true`; otherwise it is forced off even if a config file flips it on.
- Validation: `src/core/config_loader.py` (merge + directory preparation) and `src/core/startup_preflight.py` (fail-fast secret checks) are the runtime "source of truth". For local verification use `python tools/validate_config.py`. `config/schemas/app_config.py` is a legacy schema helper and should not be treated as the authoritative validator.
- Recommended setup: copy `env.example` to `.env`, fill the required secret values with strong random strings, and keep the filled file out of version control. Use `secrets.example.txt` as a checklist of sensitive keys.
- Network exposure defaults: API/server entrypoints bind to loopback by default. If you need LAN/container access, explicitly set `VCL_API_HOST=0.0.0.0` and ensure firewall/auth/rate-limit controls are enabled.
- REST API authentication: configure `VCL_API_KEYS` as a comma-separated list of API keys. If unset, a random key is generated on first start and saved under `~/.virtualchemlab/api_key.txt` for local development; production deployments must provide keys via environment variables (the service refuses to start without them).
- REST API browser access: when exposing the REST API beyond localhost, set `VCL_API_CORS_ORIGINS` to a comma-separated allowlist to avoid unintentionally allowing cross-origin requests.
- Admin API browser access: CORS is disabled by default; when exposing the admin API beyond localhost (or when you need cross-origin browser access), set `VCL_ADMIN_CORS_ORIGINS` to a comma-separated allowlist (or `*` for development) to avoid unintentionally allowing cross-origin requests.
- Development toggles: see `docs/security/development_flags.md` for opt-in demo defaults and other non-production switches.
- Source of truth for configuration/env vars: `docs/CONFIGURATION_REFERENCE.md` (kept aligned with current code paths).

## Deployment checklist

- `config/base.json`/`config/production.json` carry only env var names for secrets; real values must come from the runtime environment.
- Production startup now fails when `JWT_SECRET_KEY`/`SESSION_SECRET_KEY` are missing, or when `DEVELOPER_MODE_ENABLED=true` without `DEVELOPER_SECRET_KEY`; debug/developer flags remain off unless the env toggle is present.
- Keep `DEVELOPER_MODE_ENABLED` unset in production unless a break-glass session is intended.
- Use the refreshed `env.example`/`secrets.example.txt` as the source of truth for required secret names in CI/CD pipelines.
