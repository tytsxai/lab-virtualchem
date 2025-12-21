"""Security-related secret key loading utilities.

This module intentionally avoids any hardcoded fallback secrets. Callers must
provide a strong secret via the `VCL_SECRET_KEY` environment variable.
"""

from __future__ import annotations

import os

from src.core.common_exceptions import SecurityError


ENV_SECRET_KEY = "VCL_SECRET_KEY"
MIN_SECRET_KEY_LENGTH = 32


def get_secret_key() -> str:
    """Return the application secret key from the environment.

    Raises:
        SecurityError: If the key is missing or too weak.
    """
    secret_key = os.getenv(ENV_SECRET_KEY)
    if secret_key is None or not secret_key.strip():
        raise SecurityError(
            f"Missing required environment variable: {ENV_SECRET_KEY}",
            threat_type="missing_secret_key",
            details={"env_var": ENV_SECRET_KEY},
        )

    secret_key = secret_key.strip()
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise SecurityError(
            f"{ENV_SECRET_KEY} is too short; must be at least {MIN_SECRET_KEY_LENGTH} characters",
            threat_type="weak_secret_key",
            details={"env_var": ENV_SECRET_KEY, "min_length": MIN_SECRET_KEY_LENGTH},
        )

    return secret_key

