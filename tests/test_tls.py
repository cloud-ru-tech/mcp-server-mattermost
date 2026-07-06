"""Tests for process-wide trust-store extension (extra CA certificates)."""

import os
import ssl
from pathlib import Path

import certifi
import pytest

from mcp_server_mattermost import tls
from mcp_server_mattermost.config import Settings
from mcp_server_mattermost.exceptions import ConfigurationError


def _first_pem_cert(bundle_path: str) -> str:
    """Extract the first certificate PEM block from a bundle."""
    text = Path(bundle_path).read_text()
    begin = text.index("-----BEGIN CERTIFICATE-----")
    end = text.index("-----END CERTIFICATE-----", begin) + len("-----END CERTIFICATE-----")
    return text[begin:end] + "\n"


@pytest.fixture
def extra_ca_file(tmp_path) -> Path:
    """A valid single-CA PEM file (first cert of the certifi bundle)."""
    path = tmp_path / "extra-ca.pem"
    path.write_text(_first_pem_cert(certifi.where()))
    return path


@pytest.fixture(autouse=True)
def _reset_tls_state(monkeypatch):
    """Isolate installed-bundle state and trust-store env vars per test."""
    monkeypatch.setattr(tls, "_installed_bundle", None)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)


def _make_settings(monkeypatch, **env: str) -> Settings:
    monkeypatch.setenv("MATTERMOST_URL", "https://example.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings()


class TestInstallExtraCaCerts:
    def test_noop_when_unset(self, monkeypatch) -> None:
        settings = _make_settings(monkeypatch)

        assert tls.install_extra_ca_certs(settings) is None
        assert "SSL_CERT_FILE" not in os.environ

    def test_builds_combined_bundle(self, monkeypatch, extra_ca_file: Path) -> None:
        settings = _make_settings(monkeypatch, MATTERMOST_EXTRA_CA_CERTS=str(extra_ca_file))

        bundle_path = tls.install_extra_ca_certs(settings)

        assert bundle_path is not None
        assert os.environ["SSL_CERT_FILE"] == bundle_path
        assert os.environ["REQUESTS_CA_BUNDLE"] == bundle_path
        combined = Path(bundle_path).read_bytes()
        assert Path(certifi.where()).read_bytes().rstrip() in combined
        assert extra_ca_file.read_bytes() in combined
        # combined bundle must be loadable as a trust store
        ssl.create_default_context().load_verify_locations(cafile=bundle_path)

    def test_uses_existing_ssl_cert_file_as_base(self, monkeypatch, extra_ca_file: Path, tmp_path) -> None:
        base = tmp_path / "operator-base.pem"
        base.write_text(_first_pem_cert(certifi.where()))
        monkeypatch.setenv("SSL_CERT_FILE", str(base))
        settings = _make_settings(monkeypatch, MATTERMOST_EXTRA_CA_CERTS=str(extra_ca_file))

        bundle_path = tls.install_extra_ca_certs(settings)

        combined = Path(bundle_path).read_bytes()
        assert base.read_bytes().rstrip() in combined
        assert extra_ca_file.read_bytes() in combined

    def test_idempotent(self, monkeypatch, extra_ca_file: Path) -> None:
        settings = _make_settings(monkeypatch, MATTERMOST_EXTRA_CA_CERTS=str(extra_ca_file))

        first = tls.install_extra_ca_certs(settings)
        second = tls.install_extra_ca_certs(settings)

        assert first == second

    def test_rejects_malformed_pem(self, monkeypatch, tmp_path) -> None:
        bad = tmp_path / "not-a-cert.pem"
        bad.write_text("this is not PEM")
        settings = _make_settings(monkeypatch, MATTERMOST_EXTRA_CA_CERTS=str(bad))

        with pytest.raises(ConfigurationError, match="not a valid PEM"):
            tls.install_extra_ca_certs(settings)

        assert "SSL_CERT_FILE" not in os.environ


class TestExtraCaCertsSetting:
    def test_missing_file_rejected(self, monkeypatch) -> None:
        monkeypatch.setenv("MATTERMOST_URL", "https://example.com")
        monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
        monkeypatch.setenv("MATTERMOST_EXTRA_CA_CERTS", "/nonexistent/ca.pem")

        with pytest.raises(ValueError, match="file not found"):
            Settings()

    def test_blank_value_treated_as_unset(self, monkeypatch) -> None:
        settings = _make_settings(monkeypatch, MATTERMOST_EXTRA_CA_CERTS="  ")

        assert settings.extra_ca_certs is None

    def test_valid_path_accepted(self, monkeypatch, extra_ca_file: Path) -> None:
        settings = _make_settings(monkeypatch, MATTERMOST_EXTRA_CA_CERTS=str(extra_ca_file))

        assert settings.extra_ca_certs == str(extra_ca_file)
