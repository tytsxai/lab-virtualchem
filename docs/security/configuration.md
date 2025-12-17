# Configuration hardening

- Secrets load from environment variables. Provide `JWT_SECRET_KEY`, `SESSION_SECRET_KEY`, `DEVELOPER_SECRET_KEY`, and `VCL_ADMIN_SECRET_KEY` (or the `security.jwt_secret_env`/`developer.admin_secret_env` overrides) before starting production; the app now fails fast when they are missing.
- Configuration precedence: environment variables override `config/*.json` and `config.json`. Non-production can fall back to generated placeholders for local runs, but production never accepts file-stored secrets.
- Developer/debug defaults: production sets `app.debug=false` and `developer.enabled=false`. To explicitly enable developer mode, set `DEVELOPER_MODE_ENABLED=true`; otherwise it is forced off even if a config file flips it on.
- Validation: `config/schemas/app_config.py` enforces required env secrets for production; `Config._merge_env_vars` raises during load if JWT or admin secrets are absent so deployments fail early.
- Recommended setup: copy `env.example` to `.env`, fill the required secret values with strong random strings, and keep the filled file out of version control. Use `secrets.example.txt` as a checklist of sensitive keys.
- Network exposure defaults: API/server entrypoints bind to loopback by default. If you need LAN/container access, explicitly set `VCL_API_HOST=0.0.0.0` and ensure firewall/auth/rate-limit controls are enabled.
- REST API authentication: configure `VCL_API_KEYS` as a comma-separated list of API keys. If unset, a random key is generated on first start and saved under `~/.virtualchemlab/api_key.txt` for local development; production deployments should provide keys via environment variables.
- REST API browser access: when exposing the REST API beyond localhost, set `VCL_API_CORS_ORIGINS` to a comma-separated allowlist to avoid unintentionally allowing cross-origin requests.
- Admin API browser access: CORS is disabled by default; when exposing the admin API beyond localhost (or when you need cross-origin browser access), set `VCL_ADMIN_CORS_ORIGINS` to a comma-separated allowlist (or `*` for development) to avoid unintentionally allowing cross-origin requests.
- Development toggles: see `docs/security/development_flags.md` for opt-in demo defaults and other non-production switches.

## Deployment checklist

- `config/base.json`/`config/production.json` carry only env var names for secrets; real values must come from the runtime environment.
- Production startup now fails when `JWT_SECRET_KEY`/`SESSION_SECRET_KEY` are missing, or when `DEVELOPER_MODE_ENABLED=true` without `DEVELOPER_SECRET_KEY`; debug/developer flags remain off unless the env toggle is present.
- Keep `DEVELOPER_MODE_ENABLED`, `DEVELOPER_DEBUG`, and `DEVELOPER_CONSOLE_ENABLED` unset in production unless a break-glass session is intended.
- Use the refreshed `env.example`/`secrets.example.txt` as the source of truth for required secret names in CI/CD pipelines.
