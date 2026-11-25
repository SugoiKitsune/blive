"""Tests for :mod:`blive.adapters.ig.credentials`.

Covers the IG :class:`CredentialSchema` shape per [ADR-035](../../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)
and the typed :class:`IGCredentials` wrapper. Schema-level tests in
``test_credentials.py`` (shared) cover the generic loader; this file
focuses on IG-specific contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from blive.adapters.ig.credentials import (
    IG_SCHEMA,
    IGCredentials,
)
from blive.adapters.shared.credentials import CredentialsMissing

# --- IG_SCHEMA contract ------------------------------------------------------


def test_ig_schema_broker_name_is_ig() -> None:
    """The broker_name drives the ~/.blive/secrets/{broker}.env filename."""
    assert IG_SCHEMA.broker_name == "ig"


def test_ig_schema_required_fields_match_kb17() -> None:
    """Per KB-17 §4: 3-step auth requires API key + username + password;
    account id is needed for /accounts; environment selects URL."""
    assert set(IG_SCHEMA.required_field_names()) == {
        "IG_API_KEY",
        "IG_USERNAME",
        "IG_PASSWORD",
        "IG_ACCOUNT_ID",
        "IG_ENVIRONMENT",
    }


def test_ig_schema_secret_fields_only_credentials_proper() -> None:
    """ADR-035: API key + username + password are secrets. Account id and
    environment are NOT secrets — visible in IG UI and just 'demo'/'live'."""
    assert set(IG_SCHEMA.secret_field_names()) == {
        "IG_API_KEY",
        "IG_USERNAME",
        "IG_PASSWORD",
    }


# --- IGCredentials.load happy path ------------------------------------------


def test_load_from_env_returns_typed_credentials(tmp_path: Path) -> None:
    env = {
        "IG_API_KEY": "k",
        "IG_USERNAME": "u",
        "IG_PASSWORD": "p",
        "IG_ACCOUNT_ID": "ACC123",
        "IG_ENVIRONMENT": "demo",
    }
    creds = IGCredentials.load(secrets_dir=tmp_path, env=env)
    assert creds.api_key == "k"
    assert creds.username == "u"
    assert creds.password == "p"
    assert creds.account_id == "ACC123"
    assert creds.environment == "demo"
    assert creds.is_demo is True
    assert creds.is_live is False


def test_load_from_dotenv_file(tmp_path: Path) -> None:
    env_path = tmp_path / "ig.env"
    env_path.write_text(
        "\n".join(
            [
                "IG_API_KEY=file-k",
                "IG_USERNAME=file-u",
                "IG_PASSWORD=file-p",
                "IG_ACCOUNT_ID=file-acc",
                "IG_ENVIRONMENT=live",
            ]
        ),
        encoding="utf-8",
    )
    creds = IGCredentials.load(secrets_dir=tmp_path, env={})
    assert creds.environment == "live"
    assert creds.is_live is True
    assert creds.is_demo is False


# --- IGCredentials validation ------------------------------------------------


def test_load_missing_required_raises_credentials_missing(tmp_path: Path) -> None:
    """Generic loader raises CredentialsMissing — the typed wrapper bubbles."""
    with pytest.raises(CredentialsMissing) as excinfo:
        IGCredentials.load(secrets_dir=tmp_path, env={})
    assert excinfo.value.broker_name == "ig"


def test_load_invalid_environment_raises_value_error(tmp_path: Path) -> None:
    env = {
        "IG_API_KEY": "k",
        "IG_USERNAME": "u",
        "IG_PASSWORD": "p",
        "IG_ACCOUNT_ID": "ACC123",
        "IG_ENVIRONMENT": "production",  # invalid
    }
    with pytest.raises(ValueError, match="demo' or 'live"):
        IGCredentials.load(secrets_dir=tmp_path, env=env)


def test_direct_construction_validates_each_field() -> None:
    with pytest.raises(ValueError, match="api_key"):
        IGCredentials(
            api_key="",
            username="u",
            password="p",
            account_id="a",
            environment="demo",
        )
    with pytest.raises(ValueError, match="username"):
        IGCredentials(
            api_key="k",
            username="",
            password="p",
            account_id="a",
            environment="demo",
        )
    with pytest.raises(ValueError, match="password"):
        IGCredentials(
            api_key="k",
            username="u",
            password="",
            account_id="a",
            environment="demo",
        )
    with pytest.raises(ValueError, match="account_id"):
        IGCredentials(
            api_key="k",
            username="u",
            password="p",
            account_id="",
            environment="demo",
        )
    with pytest.raises(ValueError, match="environment"):
        IGCredentials(
            api_key="k",
            username="u",
            password="p",
            account_id="a",
            environment="staging",  # type: ignore[arg-type]
        )


def test_credentials_dataclass_is_frozen() -> None:
    creds = IGCredentials(
        api_key="k",
        username="u",
        password="p",
        account_id="a",
        environment="demo",
    )
    with pytest.raises(AttributeError):
        creds.api_key = "x"  # type: ignore[misc]
