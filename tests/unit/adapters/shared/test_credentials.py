"""Tests for :mod:`blive.adapters.shared.credentials`.

Covers [ADR-035](../../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)
contract: env-var override, dotenv fallback, required-field-missing raises,
optional-field-missing is silent, redaction-list construction across
multiple schemas. Uses ``tmp_path`` to avoid touching the real
``~/.blive/secrets/`` directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from blive.adapters.shared.credentials import (
    CredentialField,
    CredentialSchema,
    CredentialsMissing,
    default_secrets_dir,
    load_credentials,
    redaction_keys,
)

# --- Schema validation -------------------------------------------------------


def test_credential_field_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        CredentialField(name="")


def test_credential_schema_rejects_empty_broker_name() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        CredentialSchema(broker_name="", fields=())


def test_credential_schema_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValueError, match="duplicate field"):
        CredentialSchema(
            broker_name="ig",
            fields=(
                CredentialField(name="IG_API_KEY"),
                CredentialField(name="IG_API_KEY"),
            ),
        )


def test_credential_schema_helpers() -> None:
    schema = CredentialSchema(
        broker_name="ig",
        fields=(
            CredentialField(name="IG_API_KEY", required=True, secret=True),
            CredentialField(name="IG_USERNAME", required=True, secret=True),
            CredentialField(name="IG_ACCOUNT_ID", required=True, secret=False),
            CredentialField(name="IG_OPTIONAL", required=False, secret=False),
        ),
    )
    assert schema.required_field_names() == ("IG_API_KEY", "IG_USERNAME", "IG_ACCOUNT_ID")
    assert schema.secret_field_names() == ("IG_API_KEY", "IG_USERNAME")


# --- Loader: env var path ----------------------------------------------------


@pytest.fixture
def ig_schema() -> CredentialSchema:
    return CredentialSchema(
        broker_name="ig",
        fields=(
            CredentialField(name="IG_API_KEY", required=True, secret=True),
            CredentialField(name="IG_USERNAME", required=True, secret=True),
            CredentialField(name="IG_PASSWORD", required=True, secret=True),
            CredentialField(name="IG_ACCOUNT_ID", required=True, secret=False),
            CredentialField(name="IG_ENVIRONMENT", required=True, secret=False),
            CredentialField(name="IG_OPTIONAL_NOTE", required=False, secret=False),
        ),
    )


def test_load_from_env_vars(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """All required fields present in env; no file needed."""
    env = {
        "IG_API_KEY": "key-redacted",
        "IG_USERNAME": "user-redacted",
        "IG_PASSWORD": "pwd-redacted",
        "IG_ACCOUNT_ID": "demo-acc-1",
        "IG_ENVIRONMENT": "demo",
    }
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env=env)
    assert out["IG_API_KEY"] == "key-redacted"
    assert out["IG_ENVIRONMENT"] == "demo"
    # Optional field absent from env → not in result.
    assert "IG_OPTIONAL_NOTE" not in out


def test_load_from_dotenv_file(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """All required fields present in {broker}.env; env empty."""
    env_path = tmp_path / "ig.env"
    env_path.write_text(
        "\n".join(
            [
                "# blive IG demo credentials (test fixture)",
                "IG_API_KEY=file-key",
                "IG_USERNAME=file-user",
                'IG_PASSWORD="file-pwd-with-quotes"',
                "IG_ACCOUNT_ID='file-acc'",  # single-quoted
                "IG_ENVIRONMENT=demo",
                "",
                "# trailing comment",
            ]
        ),
        encoding="utf-8",
    )
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env={})
    assert out["IG_API_KEY"] == "file-key"
    assert out["IG_PASSWORD"] == "file-pwd-with-quotes", "double quotes should be stripped"
    assert out["IG_ACCOUNT_ID"] == "file-acc", "single quotes should be stripped"
    assert "IG_OPTIONAL_NOTE" not in out


def test_env_overrides_file(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """Env-var value beats file value for the same key."""
    env_path = tmp_path / "ig.env"
    env_path.write_text(
        "\n".join(
            [
                "IG_API_KEY=file-key",
                "IG_USERNAME=file-user",
                "IG_PASSWORD=file-pwd",
                "IG_ACCOUNT_ID=file-acc",
                "IG_ENVIRONMENT=demo",
            ]
        ),
        encoding="utf-8",
    )
    env = {"IG_API_KEY": "env-key"}
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env=env)
    assert out["IG_API_KEY"] == "env-key", "env should override file"
    assert out["IG_USERNAME"] == "file-user", "file value used when env doesn't have key"


def test_missing_required_raises_with_path(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """All required fields missing → CredentialsMissing names the file path."""
    with pytest.raises(CredentialsMissing) as excinfo:
        load_credentials(ig_schema, secrets_dir=tmp_path, env={})
    assert excinfo.value.broker_name == "ig"
    assert "IG_API_KEY" in excinfo.value.missing
    assert excinfo.value.env_path == tmp_path / "ig.env"
    # Optional field is NOT in missing.
    assert "IG_OPTIONAL_NOTE" not in excinfo.value.missing


def test_partial_missing_required_raises(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """Some required fields present, some missing → still raises with the missing ones."""
    env = {
        "IG_API_KEY": "key",
        "IG_USERNAME": "user",
        # missing PASSWORD, ACCOUNT_ID, ENVIRONMENT
    }
    with pytest.raises(CredentialsMissing) as excinfo:
        load_credentials(ig_schema, secrets_dir=tmp_path, env=env)
    assert set(excinfo.value.missing) == {"IG_PASSWORD", "IG_ACCOUNT_ID", "IG_ENVIRONMENT"}


def test_optional_field_in_env_is_returned(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """When optional field IS provided, it appears in the result."""
    env = {
        "IG_API_KEY": "key",
        "IG_USERNAME": "user",
        "IG_PASSWORD": "pwd",
        "IG_ACCOUNT_ID": "acc",
        "IG_ENVIRONMENT": "demo",
        "IG_OPTIONAL_NOTE": "this is fine",
    }
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env=env)
    assert out["IG_OPTIONAL_NOTE"] == "this is fine"


def test_unrelated_env_vars_ignored(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    """The loader doesn't pass through env vars not in the schema."""
    env = {
        "IG_API_KEY": "k",
        "IG_USERNAME": "u",
        "IG_PASSWORD": "p",
        "IG_ACCOUNT_ID": "a",
        "IG_ENVIRONMENT": "demo",
        "PATH": "/usr/bin",
        "HOME": "/home/oleg",
        "RANDOM_THING": "should not appear",
    }
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env=env)
    assert "PATH" not in out
    assert "HOME" not in out
    assert "RANDOM_THING" not in out


# --- .env parser edge cases -------------------------------------------------


def test_dotenv_parser_handles_comments_blanks_and_malformed_lines(
    ig_schema: CredentialSchema, tmp_path: Path
) -> None:
    env_path = tmp_path / "ig.env"
    env_path.write_text(
        "\n".join(
            [
                "# Top comment",
                "",
                "IG_API_KEY=key1",
                "  # indented comment",
                "MALFORMED_LINE_NO_EQUALS",  # silently skipped per loader spec
                "IG_USERNAME=user1",
                "=value-with-no-key",  # silently skipped
                "IG_PASSWORD=pwd1",
                "IG_ACCOUNT_ID=acc1",
                "IG_ENVIRONMENT=demo",
                "",
            ]
        ),
        encoding="utf-8",
    )
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env={})
    assert out["IG_API_KEY"] == "key1"
    assert out["IG_USERNAME"] == "user1"


def test_dotenv_parser_strips_outer_whitespace(ig_schema: CredentialSchema, tmp_path: Path) -> None:
    env_path = tmp_path / "ig.env"
    env_path.write_text(
        "\n".join(
            [
                "  IG_API_KEY  =  key-with-spaces  ",
                "IG_USERNAME=user1",
                "IG_PASSWORD=pwd1",
                "IG_ACCOUNT_ID=acc1",
                "IG_ENVIRONMENT=demo",
            ]
        ),
        encoding="utf-8",
    )
    out = load_credentials(ig_schema, secrets_dir=tmp_path, env={})
    assert out["IG_API_KEY"] == "key-with-spaces"


# --- Default secrets dir ----------------------------------------------------


def test_default_secrets_dir_is_home_blive_secrets() -> None:
    """default_secrets_dir() returns ~/.blive/secrets/ for the current user."""
    expected = Path.home() / ".blive" / "secrets"
    assert default_secrets_dir() == expected


# --- Redaction-list construction --------------------------------------------


def test_redaction_keys_union_across_schemas() -> None:
    ig_schema = CredentialSchema(
        broker_name="ig",
        fields=(
            CredentialField(name="IG_API_KEY", secret=True),
            CredentialField(name="IG_PASSWORD", secret=True),
            CredentialField(name="IG_ACCOUNT_ID", secret=False),  # not redacted
        ),
    )
    ib_schema = CredentialSchema(
        broker_name="ib",
        fields=(
            CredentialField(name="IB_HOST", secret=False),
            CredentialField(name="IB_CLIENT_ID", secret=False),
            CredentialField(name="IB_PAPER_ACCOUNT_ID", secret=True),
        ),
    )
    keys = redaction_keys(ig_schema, ib_schema)
    assert keys == frozenset({"IG_API_KEY", "IG_PASSWORD", "IB_PAPER_ACCOUNT_ID"})


def test_redaction_keys_empty_input() -> None:
    assert redaction_keys() == frozenset()
