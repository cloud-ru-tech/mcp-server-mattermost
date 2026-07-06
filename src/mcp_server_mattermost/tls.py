"""Process-wide trust-store extension for outgoing HTTPS clients."""

import os
import ssl
import tempfile
from pathlib import Path

import certifi

from .config import Settings
from .logging import logger


_installed_bundle: str | None = None


def install_extra_ca_certs(settings: Settings) -> str | None:
    """Extend the default trust store with the CAs from ``extra_ca_certs``.

    ``SSL_CERT_FILE`` / ``REQUESTS_CA_BUNDLE`` *replace* the trust store used
    by httpx and other OpenSSL-based clients rather than extending it, so
    pointing them at a corporate-CA-only file silently breaks TLS to hosts
    with publicly-signed certificates. To get append semantics, this builds a
    combined PEM bundle — the current default bundle (an operator-provided
    ``SSL_CERT_FILE`` or certifi's) plus the extra CAs — and points those
    variables at it.

    Must run before any HTTP client is created. Safe to call more than once;
    subsequent calls return the already-installed bundle path.

    Args:
        settings: Validated application settings.

    Returns:
        Path of the combined bundle, or None when ``extra_ca_certs`` is unset.

    Raises:
        ConfigurationError: If the extra CA file is not valid PEM.
    """
    global _installed_bundle  # noqa: PLW0603
    if not settings.extra_ca_certs:
        return None
    if _installed_bundle is not None:
        return _installed_bundle

    extra_path = Path(settings.extra_ca_certs)
    try:
        ssl.create_default_context().load_verify_locations(cafile=str(extra_path))
    except ssl.SSLError as e:
        from .exceptions import ConfigurationError  # noqa: PLC0415

        msg = f"MATTERMOST_EXTRA_CA_CERTS is not a valid PEM CA bundle: {extra_path}"
        raise ConfigurationError(msg) from e

    base_path = Path(os.environ.get("SSL_CERT_FILE") or certifi.where())
    with tempfile.NamedTemporaryFile("wb", prefix="mattermost-mcp-ca-", suffix=".pem", delete=False) as bundle:
        bundle.write(base_path.read_bytes().rstrip() + b"\n")
        bundle.write(extra_path.read_bytes())
        bundle_path = bundle.name

    os.environ["SSL_CERT_FILE"] = bundle_path
    os.environ["REQUESTS_CA_BUNDLE"] = bundle_path
    _installed_bundle = bundle_path
    logger.info("Trust store extended with extra CAs from %s", extra_path)
    return bundle_path
