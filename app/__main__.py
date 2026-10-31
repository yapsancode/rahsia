"""Start the app: python -m app --port 8001

Each person runs this on their own laptop. The page is served to this laptop only.
"""
import argparse
import threading
import webbrowser

import uvicorn

from profile_builder.builder import DEFAULT_MODEL
from profile_builder.client import warm_up

HOST = "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(prog="app", description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--open", action="store_true", help="open the browser when the app starts")
    args = parser.parse_args()

    if args.open:
        threading.Timer(1.0, webbrowser.open, [f"http://{HOST}:{args.port}"]).start()
    threading.Thread(target=warm_up, args=[DEFAULT_MODEL], daemon=True).start()
    print(f"Rahsia is running at http://{HOST}:{args.port}")
    uvicorn.run("app.server:app", host=HOST, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
