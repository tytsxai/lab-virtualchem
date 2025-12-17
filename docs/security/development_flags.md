# Development-only security toggles

These environment variables exist to support local demos and development workflows. Do not enable them in production.

## Demo authentication

- `VCL_DEMO_AUTH_ENABLED=1`: enables a demo-only credential check in the enhanced security manager. Without this flag, demo credential verification is intentionally disabled to avoid weak-password defaults.

## Default users

- `VCL_CREATE_DEFAULT_USERS=1`: enables creation of built-in `admin`/`user` accounts for development. When enabled, you must also provide:
  - `VCL_DEFAULT_ADMIN_PASSWORD`
  - `VCL_DEFAULT_USER_PASSWORD`

If these passwords are missing while the flag is enabled, startup will fail fast with a clear error.
