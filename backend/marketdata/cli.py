from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

from marketdata import store
from marketdata.provider import fetch_ohlcv
from marketdata.quality import quality_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Market-data pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "quality"):
        p = sub.add_parser(name)
        p.add_argument("--symbol", default="BTC/USDT")
        p.add_argument("--timeframe", default="1h")
        if name == "fetch":
            p.add_argument("--exchange", default="binance")
            p.add_argument("--days", type=int, default=90)
    args = parser.parse_args(argv)

    store.init_db()
    if args.cmd == "fetch":
        start = datetime.now(UTC) - timedelta(days=args.days)
        frame = fetch_ohlcv(args.symbol, args.timeframe, start, exchange_id=args.exchange)
        saved = store.upsert_candles(frame, args.symbol, args.timeframe)
        print(f"stored {saved} candles for {args.symbol} {args.timeframe}")
        print(json.dumps(quality_report(frame, args.timeframe), indent=2))
    else:
        print(json.dumps(quality_report(store.load_candles(args.symbol, args.timeframe), args.timeframe), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
