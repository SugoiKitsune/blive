"""IG credential schema + typed loader.

Declares :data:`IG_SCHEMA`, the per-broker
:class:`blive.adapters.shared.credentials.CredentialSchema` for IG. Field
set lifted from [KB-17 §4](../../../../docs/kb/ig_pacing_spec.md#4-session-token-lifecycle):
the 3-step REST auth requires API key + username + password; the account
id is needed for ``GET /accounts/{accountId}/...``; the environment
selector ("demo" / "live") drives URL routing per [KB-16 §1](../../../../docs/kb/ig_capability_matrix.md#1-connectivity-surface).

The :class:`IGCredentials` dataclass wraps :func:`load_credentials` with a
typed result. Construction validates that ``IG_ENVIRONMENT`` is one of
``"demo"`` / ``"live"`` (semantic validation that the generic loader does
not perform).

Per [ADR-035](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets):
``IG_API_KEY`` / ``IG_USERNAME`` / ``IG_PASSWORD`` are marked ``secret=True``
so they enter the log-redaction list. ``IG_ACCOUNT_ID`` and ``IG_ENVIRONMENT``
are marked ``secret=False`` — the account id is visible in IG's own UI and
the environment is just ``"demo"`` / ``"live"``; redacting them would only
make logs harder to read without protecting anything sensitive.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from blive.adapters.shared.credentials import (
    CredentialField,
    CredentialSchema,
    load_credentials,
)

# --- Schema (consumed by load_credentials) ----------------------------------

IG_SCHEMA: CredentialSchema = CredentialSchema(
    broker_name="ig",
    fields=(
        CredentialField(name="IG_API_KEY", required=True, secret=True),
        CredentialField(name="IG_USERNAME", required=True, secret=True),
        CredentialField(name="IG_PASSWORD", required=True, secret=True),
        CredentialField(name="IG_ACCOUNT_ID", required=True, secret=False),
        CredentialField(name="IG_ENVIRONMENT", required=True, secret=False),
    ),
)


# --- Typed wrapper -----------------------------------------------------------

IGEnvironment = Literal["demo", "live"]


@dataclass(frozen=True, slots=True)
class IGCredentials:
    """Typed credentials bundle for the IG adapter.

    Construct via :meth:`load` to read from env / dotenv. The dataclass
    itself is dumb data — validation happens once at :meth:`load` time so
    the rest of the adapter can trust the values.
    """

    api_key: str
    username: str
    password: str
    account_id: str
    environment: IGEnvironment

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("IGCredentials.api_key must be non-empty")
        if not self.username:
            raise ValueError("IGCredentials.username must be non-empty")
        if not self.password:
            raise ValueError("IGCredentials.password must be non-empty")
        if not self.account_id:
            raise ValueError("IGCredentials.account_id must be non-empty")
        if self.environment not in ("demo", "live"):
            raise ValueError(
                f"IGCredentials.environment must be 'demo' or 'live', got {self.environment!r}"
            )

    @classmethod
    def load(
        cls,
        *,
        secrets_dir: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> "IGCredentials":
        """Load from ``~/.blive/secrets/ig.env`` (or env vars) per ADR-035.

        Raises :class:`blive.adapters.shared.credentials.CredentialsMissing`
        if any required field is unavailable; raises :class:`ValueError`
        if ``IG_ENVIRONMENT`` is anything other than ``"demo"`` / ``"live"``.
        """
        raw = load_credentials(IG_SCHEMA, secrets_dir=secrets_dir, env=env)
        return cls(
            api_key=raw["IG_API_KEY"],
            username=raw["IG_USERNAME"],
            password=raw["IG_PASSWORD"],
            account_id=raw["IG_ACCOUNT_ID"],
            environment=_validate_environment(raw["IG_ENVIRONMENT"]),
        )

    @property
    def is_demo(self) -> bool:
        return self.environment == "demo"

    @property
    def is_live(self) -> bool:
        return self.environment == "live"


def _validate_environment(value: str) -> IGEnvironment:
    if value == "demo":
        return "demo"
    if value == "live":
        return "live"
    raise ValueError(f"IG_ENVIRONMENT must be 'demo' or 'live', got {value!r}")


__all__ = [
    "IG_SCHEMA",
    "IGCredentials",
    "IGEnvironment",
]
