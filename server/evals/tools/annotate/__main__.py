"""annotate UI のローカル起動。

bind は loopback 固定。正本 jsonl を無認証で書き換えるため、外部に出す経路を作らない。
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from evals.tools.annotate.app import create_app

_HOST = "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="evals.tools.annotate", description="正本 jsonl の annotate をブラウザで行う"
    )
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--no-browser", action="store_true", help="起動時にブラウザを開かない")
    args = parser.parse_args()

    url = f"http://{_HOST}:{args.port}"
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, (url,)).start()
    print(f"annotate UI: {url}")
    uvicorn.run(create_app(), host=_HOST, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
