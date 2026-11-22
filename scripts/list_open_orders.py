"""List the orders WORKING at IB for the configured account — read-only, nothing is placed or changed.

    python scripts/list_open_orders.py            # paper account (~/.blive/secrets/ib.env)
    python scripts/list_open_orders.py --live     # live account (~/.blive/secrets/live/ib.env)

Prints a JSON block between ===OPEN_ORDERS_JSON=== markers (the sfera Execution tab renders it):
{account, gateway, asof, orders: [{symbol, side, qty, filled, remaining, type, tif, limit, status, ref, account}]}
Only orders of the configured account are listed (a login can serve several accounts).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import ib_async

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from blive.adapters.ib.credentials import IBCredentials  # noqa: E402

LIVE_DIR = Path.home() / ".blive" / "secrets" / "live"


async def main(live: bool) -> int:
    cred = IBCredentials.load(secrets_dir=LIVE_DIR, env={}) if live else IBCredentials.load()
    ib = ib_async.IB()
    try:
        # own client id (+20) so it never collides with the executor's session; readonly = cannot place orders
        await ib.connectAsync(cred.host, cred.port, clientId=cred.client_id + 20, readonly=True, timeout=15)
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: cannot reach the {'LIVE' if live else 'paper'} Gateway at {cred.host}:{cred.port}: {exc}")
        return 3
    try:
        if cred.account_id not in ib.managedAccounts():
            print(f"FAILED: Gateway serves {ib.managedAccounts()}, not {cred.account_id}")
            return 3
        try:
            trades = await asyncio.wait_for(ib.reqAllOpenOrdersAsync(), timeout=20)
        except asyncio.TimeoutError:
            print("FAILED: the Gateway is connected but IB did not answer the open-orders request in 20s "
                  "(server maintenance / Gateway lost its IB connection?) — check the Gateway window.")
            return 4
        rows = []
        for t in trades:
            o, c, s = t.order, t.contract, t.orderStatus
            if (o.account or cred.account_id) != cred.account_id:
                continue
            rows.append({"symbol": c.symbol, "side": o.action, "qty": float(o.totalQuantity),
                         "filled": float(s.filled or 0), "remaining": float(s.remaining or 0),
                         "type": o.orderType, "tif": o.tif,
                         "limit": (float(o.lmtPrice) if o.orderType in ("LMT", "LOO") and o.lmtPrice < 1e300 else None),
                         "status": s.status, "ref": o.orderRef or "", "account": o.account or cred.account_id})
        out = {"account": cred.account_id, "gateway": f"{cred.host}:{cred.port}", "live": live,
               "asof": datetime.now(timezone.utc).isoformat(timespec="seconds"), "orders": rows}
        print("===OPEN_ORDERS_JSON===")
        print(json.dumps(out))
        print("===END_OPEN_ORDERS_JSON===")
        print(f"{len(rows)} open order(s) on {cred.account_id}")
        return 0
    finally:
        ib.disconnect()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    sys.exit(asyncio.run(main(ap.parse_args().live)))
