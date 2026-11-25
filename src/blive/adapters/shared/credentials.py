"""Broker-agnostic credentials loader.

Implements [ADR-035 Secrets handling discipline](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).

Each broker adapter declares a per-broker :class:`CredentialSchema` describing
the credential fields it requires; the shared loader resolves the values
from environment variables (highest priority), falling back to a
``~/.blive/secrets/{broker}.env`` file. Missing required fields raise
:class:`CredentialsMissing` with a human-readable message naming the file
the operator should populate.

The loader **never logs values**. The schema's :meth:`CredentialSchema.secret_field_names`
helper returns the redaction list that ``blive.utils.logging`` (M2-IG.3
deliverable) consumes when redacting log messages.

The discipline binding the agent ([ADR-035 §"Decision" item 6](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)):
the agent does not echo credentials it has been told and does not write
them into any file in the repo. This module enforces the read-side of
that contract — credential values never leave the returned mapping.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

# --- Credential schema -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CredentialField:
    """One field in a per-broker credential schema."""

    name: str
    """Env-var name (e.g. ``"IG_API_KEY"``); also the key in ``{broker}.env``."""

    required: bool = True
    """When True, missing-everywhere raises ``CredentialsMissing``. When False, absence is silent."""

    secret: bool = True
    """Whether this field's *value* should be redacted in logs. Set False for non-sensitive
    fields like ``IG_ENVIRONMENT`` ('demo' / 'live') or ``IG_ACCOUNT_ID`` (account identifier
    visible in IG's UI). Defaults to True — when in doubt, redact."""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("CredentialField.name must be non-empty")


@dataclass(frozen=True, slots=True)
class CredentialSchema:
    """A per-broker credential schema. Declared in ``blive.adapters.{broker}.credentials``."""

    broker_name: str
    """Which broker the schema describes. Drives the ``~/.blive/secrets/{broker}.env`` filename."""

    fields: tuple[CredentialField, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.broker_name:
            raise ValueError("CredentialSchema.broker_name must be non-empty")
        # Disallow duplicate field names — would cause ambiguous overrides.
        seen: set[str] = set()
        for f in self.fields:
            if f.name in seen:
                raise ValueError(
                    f"CredentialSchema for {self.broker_name!r} has duplicate field {f.name!r}"
                )
            seen.add(f.name)

    def required_field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields if f.required)

    def secret_field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields if f.secret)


# --- Errors ------------------------------------------------------------------


class CredentialsMissing(Exception):
    """Raised when one or more required credential fields are not available.

    Carries the broker name, the missing field names, and the path the
    operator should populate.
    """

    def __init__(
        self,
        broker_name: str,
        missing: list[str],
        env_path: Path,
    ) -> None:
        self.broker_name = broker_name
        self.missing = list(missing)
        self.env_path = env_path
        super().__init__(
            f"missing required credentials for broker {broker_name!r}: {sorted(missing)}. "
            f"Set as environment variables or place values in {env_path} "
            f"(KEY=VALUE per line; chmod 600)."
        )


# --- Public loader -----------------------------------------------------------


def default_secrets_dir() -> Path:
    """Return ``~/.blive/secrets/`` resolved against the current user's home directory."""
    return Path.home() / ".blive" / "secrets"


def load_credentials(
    schema: CredentialSchema,
    *,
    secrets_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    """Resolve credentials for the given schema.

    Resolution order (highest priority first):

    1. **Environment variables** matching field names (``schema.fields[i].name``).
       This lets Docker / systemd / CI inject credentials without writing files.
    2. **``{secrets_dir}/{schema.broker_name}.env``** — KEY=VALUE per line; ``#``
       comments and blank lines ignored; values may be optionally surrounded by
       ``"..."`` or ``'...'`` quotes.

    Missing **required** fields raise :class:`CredentialsMissing`. Missing
    optional fields are simply absent from the returned mapping.

    Returns a mapping ``{field.name: value}``. The dict is plain; callers may
    consume it in their own per-broker `Credentials` dataclass construction.

    The returned mapping never includes a value for a field whose name is not
    in the schema; the loader does not pass through unrelated env vars.
    """
    env_map: Mapping[str, str] = env if env is not None else os.environ
    sdir = secrets_dir if secrets_dir is not None else default_secrets_dir()
    env_path = sdir / f"{schema.broker_name}.env"

    file_values: dict[str, str] = {}
    if env_path.is_file():
        file_values = _parse_dotenv(env_path)

    out: dict[str, str] = {}
    missing: list[str] = []
    for f in schema.fields:
        if f.name in env_map:
            out[f.name] = env_map[f.name]
        elif f.name in file_values:
            out[f.name] = file_values[f.name]
        elif f.required:
            missing.append(f.name)

    if missing:
        raise CredentialsMissing(schema.broker_name, missing, env_path)
    return out


def redaction_keys(*schemas: CredentialSchema) -> frozenset[str]:
    """Return the union of secret-field names across the provided schemas.

    Consumed by the (forthcoming) ``blive.utils.logging`` redaction layer at
    process start. New brokers add their schemas to the call site; missing one
    is detectable as an inventory drift via the schema-walk in M5+ tests.
    """
    out: set[str] = set()
    for schema in schemas:
        out.update(schema.secret_field_names())
    return frozenset(out)


# --- Internals ---------------------------------------------------------------


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser: KEY=VALUE per line; ``#`` comments; blank lines ignored.

    Optional surrounding double or single quotes on the value are stripped.
    Lines without ``=`` are silently skipped (not raised on) so a partial /
    in-progress edit doesn't break loading the rest of the file.

    Read in UTF-8; on encoding error the loader bubbles the exception.
    """
    out: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        # Strip surrounding quote pairs (both " and ' supported).
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        out[key] = value
    return out


__all__ = [
    "CredentialField",
    "CredentialSchema",
    "CredentialsMissing",
    "default_secrets_dir",
    "load_credentials",
    "redaction_keys",
]
