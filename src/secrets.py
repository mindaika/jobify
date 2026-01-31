"""
Secrets management utility for handling Docker secrets and environment variables.

This module provides a unified way to read secrets from Docker secret files
(in production) or fall back to environment variables (in development).
"""
import os
from typing import Optional


def get_secret(secret_name: str, env_var_name: Optional[str] = None) -> str:
    """
    Read secret from Docker secret file or fall back to environment variable.

    In production with Docker secrets, secrets are mounted as files in /run/secrets/.
    In development, we fall back to environment variables.

    Args:
        secret_name: Name of the Docker secret (e.g., 'anthropic_api_key')
        env_var_name: Optional environment variable name to use as fallback
                     (e.g., 'ANTHROPIC_API_KEY'). If None, uppercase secret_name is used.

    Returns:
        str: The secret value

    Raises:
        ValueError: If secret is not found in either location

    Examples:
        >>> # Read Anthropic API key from Docker secret or ANTHROPIC_API_KEY env var
        >>> api_key = get_secret('anthropic_api_key', 'ANTHROPIC_API_KEY')

        >>> # Read secret with auto-generated env var name (ANTHROPIC_API_KEY)
        >>> api_key = get_secret('anthropic_api_key')
    """
    # Try reading from Docker secret file first
    secret_file = f"/run/secrets/{secret_name}"

    if os.path.exists(secret_file):
        try:
            with open(secret_file, 'r') as f:
                secret_value = f.read().strip()
                if secret_value:
                    return secret_value
        except (IOError, OSError) as e:
            # If we can't read the file, fall through to environment variable
            pass

    # Fall back to environment variable
    if env_var_name is None:
        # Auto-generate env var name: anthropic_api_key -> ANTHROPIC_API_KEY
        env_var_name = secret_name.upper()

    env_value = os.environ.get(env_var_name)
    if env_value:
        return env_value

    # Neither Docker secret nor environment variable found
    raise ValueError(
        f"Secret '{secret_name}' not found. "
        f"Looked for Docker secret at {secret_file} and environment variable {env_var_name}"
    )


def get_anthropic_api_key() -> str:
    """
    Get Anthropic API key from Docker secret or environment variable.

    Returns:
        str: Anthropic API key

    Raises:
        ValueError: If API key is not found
    """
    return get_secret('anthropic_api_key', 'ANTHROPIC_API_KEY')
