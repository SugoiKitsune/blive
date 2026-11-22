"""Health of the paper and live IB Gateways — read-only, nothing is placed.

For each configured Gateway (paper: ~/.blive/secrets/ib.env, live: ~/.blive/secrets/live/ib.env):
    running   the API port accepts a TCP connection
    api       an API session opens (handshake) and reports its managed accounts
    account   the configured account is among them
    servers   IB's servers answer a request through the Gateway (positions) — a Gateway can be up and connected
              while IB is down for maintenance, which is exactly when an order would silently go nowhere
Prints a JSON block between ===GATEWAY_STATUS_JSON=== markers (rendered by the sfera Execution tab).

    python scripts/gateway_status.py
"""
from __future__ import annotations

import asyncio
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ib_async  # noqa: E402

from blive.adapters.ib.credentials import IBCredentials  # noqa: E402

LIVE_DIR = Path.home() / ".blive" / "secrets" / "live"


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


async def _check(mode: str) -> dict:
    out = {"mode": mode, "running": False, "api": False, "account_ok": False, "servers": False,
           "account": None, "managed": [], "gateway": None, "latency_ms": None, "detail": ""}
    try:
        cred = IBCredentials.load(secrets_dir=LIVE_DIR, env={}) if mode == "live" else IBCredentials.load()
    except Exception as exc:  # noqa: BLE001
        out["detail"] = f"no {mode} credentials file: {exc}"
        return out
    out["account"], out["gateway"] = cred.account_id, f"{cred.host}:{cred.port}"
    if not _port_open(cred.host, cred.port):
        out["detail"] = "Gateway not running (port closed)"
        return out
    out["running"] = True
    ib = ib_async.IB()
    t0 = time.perf_counter()
    try:
        # +30: never collides with the executor (+0) or the open-orders viewer (+20); readonly cannot trade
        await asyncio.wait_for(ib.connectAsync(cred.host, cred.port, clientId=cred.client_id + 30, readonly=True,
                                               timeout=8), timeout=12)
        out["api"] = True
        out["managed"] = list(ib.managedAccounts())
        out["account_ok"] = cred.account_id in out["managed"]
        try:
            await asyncio.wait_for(ib.reqPositionsAsync(), timeout=6)
            out["servers"] = True
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        except asyncio.TimeoutError:
            out["detail"] = "Gateway up but IB servers not answering (maintenance / lost connection)"
        if not out["account_ok"]:
            out["detail"] = f"Gateway serves {out['managed']}, not {cred.account_id}"
    except Exception as exc:  # noqa: BLE001
        out["detail"] = f"API handshake failed: {type(exc).__name__}: {exc}"[:200]
    finally:
        try:
            ib.disconnect()
        except Exception:  # noqa: BLE001
            pass
    return out


async def main() -> int:
    res = await asyncio.gather(_check("paper"), _check("live"))
    print("===GATEWAY_STATUS_JSON===")
    print(json.dumps({"asof": datetime.now(timezone.utc).isoformat(timespec="seconds"), "gateways": res}))
    print("===END_GATEWAY_STATUS_JSON===")
    return 0


if __name__ == "__main__":
    import logging
    logging.disable(logging.CRITICAL)        # ib_async chatter (timeouts are reported in the JSON)
    sys.exit(asyncio.run(main()))
