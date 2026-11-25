---
id: CLAUDE.md
title: Session-bootstrap pointer for Claude Code
status: STABLE
owner: Oleg
last_reviewed: 2026-05-02
version: 1.0
sources:
  - CONTEXT_PROTOCOL.md §8.1 (warm-up)
  - ADR-042 (session-bootstrap pattern)
depends_on:
  - CONTEXT_PROTOCOL
  - CONTEXT_INVENTORY
  - REQUIREMENTS
  - TASK_REGISTRY
  - NEXT_PROMPT
referenced_by:
  - CONTEXT_INVENTORY.md §1 (Layer 0. Bootstrap)
---

# Project instructions

You are working on `blive` — a multi-broker live execution engine, sibling to `btest`. The supported brokers are configured via the multi-broker registry pattern in [ADR-034](docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004); current first-class adapters are **Interactive Brokers (IB)** and **IG**, plus paper / mock for development. The active integration focus is IB (per `TASK_REGISTRY.md` M2-IB); the IG adapter is in the repo and supported as a first-class broker (its M2-IG.5 strategy-run sub-milestone is the part that was deferred, not the adapter itself). This project enforces a substrate-engineering discipline called **Cognitive Cartography**, articulated in [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) and the methodology paper at [`docs/method/paper/cognitive_cartography.tex`](docs/method/paper/cognitive_cartography.tex). Every edit to docs and code follows it.

This file is a **session-bootstrap pointer** ([ADR-042](docs/decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point)). Its content is *pointers* to canonical substrate, never restated rules — the protocol is the SSOT.

## Mandatory warm-up at session start (CONTEXT_PROTOCOL §8.1)

Before any edit, in this order:

1. Read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) — at minimum §0 TL;DR + §3 edit protocol + §3.5 anti-patterns. Re-read in full if it's been > 1 week or if any §11 change is unfamiliar.
2. Read [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) end-to-end. §10 "Priority Queue" tells you where the project is right now.
3. Read [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) for the active milestone's plan + exit criteria.
4. Read [`NEXT_PROMPT.md`](./NEXT_PROMPT.md) — the current session's specific mission.
5. For artefacts the task touches: read frontmatter + body, then any KB / INV / DD / ADR / OQ they cite. Spawn an `Explore` sub-agent for breadth if ≥ 4 artefacts need to be read.
6. Reply with a 5-line warm-up summary: artefacts read, project state in one sentence, first concrete action. Wait for "go" before code.

Skipping warm-up is a correction. Resuming yesterday's task is **not** an exemption — re-warm-up.

## Discipline at-a-glance

- **Stable IDs always.** Cite `KB-3`, `ADR-032`, `INV-14`, `OQ-030` in chat, comments, and commit messages. Never file paths or section numbers.
- **SSOT.** A fact has one home. Duplicates are the bug, not the disagreement.
- **Append-only.** Reverse an ADR via a new ADR with `supersedes: ADR-NNN`; never edit a past ADR's body. Same for OQs and RETROs.
- **ADR for every architectural choice.** If a non-trivial choice arises that isn't already in [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md), stop: draft a `PROPOSED` ADR, surface it, wait for confirmation before committing.
- **OQ for every unresolved question.** With a target resolution date.
- **Status lifecycle.** `MISSING → DRAFT → STABLE → STALE → DEPRECATED`. Bump `last_reviewed` on every edit; bump `version` if substantive.
- **Commit messages list artefacts touched by stable ID.** Format:

  ```
  [blive] Brief summary

  - Touched: KB-3 (added pacing source), DD-1 (Instrument.tradability).
  - New: ADR-NNN (chose token-bucket over sliding-window).
  - Status changes: KB-3 DRAFT → STABLE.
  ```
- **Trivial-fix lane** ([CONTEXT_PROTOCOL §3.4](./CONTEXT_PROTOCOL.md)) for typos / formatting / non-meaning-changing fixes only.

## Layer purity

Hexagonal: `blive.domain.*` → ports; `blive.adapters.*` → ports. The domain never imports adapters or third-party broker libraries. Enforced by `import-linter` in CI; `uv run lint-imports` should always KEEP every contract.

## Toolchain

- Python **3.12.x** (3.11 still resolvable during the transition — see [ADR-053](docs/decisions/DECISIONS.md#adr-053--upgrade-to-python-312)). `uv sync --extra dev` then `uv run pytest -q`.
- Pre-commit gates: `pytest`, `mypy --strict`, `lint-imports`, `black --check`, `isort --check-only`.
- If a gate fails, fix the root cause; never bypass with `--no-verify` or `--no-gpg-sign`.

## Milestone close ceremony ([CONTEXT_PROTOCOL §8.3.1](./CONTEXT_PROTOCOL.md))

If your session closes a milestone:

1. Write `docs/retros/M{N}_retrospective.md` per [`docs/retros/_template.md`](docs/retros/_template.md) — frozen on first write.
2. Update [`NEXT_PROMPT.md`](./NEXT_PROMPT.md) to target M_{N+1}, informed by the retro.
3. Report gate status as a checklist (passed / partial / blocked, reason per line).

Phase boundaries (e.g., M3 → Phase 2 entry) require **three separate sessions** — implementation close, readiness audit, plan-drafting. Mixing modes is forbidden ([CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md)).

## When to ask vs. when to act

- **Risky / hard-to-reverse / shared-state** actions (force push, deleting branches, rewriting committed history, dropping IB connections mid-session, modifying CI / hooks, real-money trading): ask first.
- **Local reversible** actions (file edits, running tests, drafting artefacts in-session): proceed; surface what you did.
- **Architectural choices not in ADR-001..N**: stop, draft `PROPOSED`, surface, wait. Don't ad-hoc.
- **Anything blocked on operator action** (IB Gateway config, secrets, market-data subscription, broker-side API toggles): surface in the warm-up summary; don't guess.

## Key pointers

| Topic | Where |
|-------|-------|
| Methodology paper (deeper "why") | [`docs/method/paper/cognitive_cartography.tex`](docs/method/paper/cognitive_cartography.tex) + [`Amendments_Log.md`](docs/method/Amendments_Log.md) |
| Glossary (authoritative on terms) | [`docs/GLOSSARY.md`](docs/GLOSSARY.md) (KB-12) |
| Architectural decisions | [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md) (KB-10) |
| Open questions | [`docs/decisions/OPEN_QUESTIONS.md`](docs/decisions/OPEN_QUESTIONS.md) (KB-11) |
| Retros | [`docs/retros/`](docs/retros/) |
| Phase-1 readiness | [`docs/PHASE_1_READINESS.md`](docs/PHASE_1_READINESS.md) |

## Note for non-Claude agents

This file is the Claude Code instance of the bootstrap-file pattern ([ADR-042](docs/decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point)). The pattern is **agent-agnostic**; if you arrive via a different harness (Cursor, OpenAI Codex, Gemini CLI, IDE assistants, etc.), the *content above is still the contract* — only the loader filename differs by convention. A second instance for another harness can be added as a thin shim around the same pointers when a second platform is in regular use.

## Changelog

- **v1.0 (2026-05-02)** — initial write. Operationalises [CONTEXT_PROTOCOL §8.1](./CONTEXT_PROTOCOL.md) warm-up + §11.2 L0 baseline per ADR-042. First instance of the session-bootstrap-file pattern.
- **v1.0.1 (2026-05-02)** — opening sentence corrected: blive is a *multi-broker* live execution engine (per [ADR-034](docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)). The prior wording said "for Interactive Brokers", which conflated the v1 / current-focus broker (IB) with the engine's actual scope (IB + IG + paper/mock). No semantic change to the discipline.
