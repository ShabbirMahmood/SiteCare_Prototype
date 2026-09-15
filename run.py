"""Start the desktop-local SiteCare server. Keep this terminal open while in use."""
from __future__ import annotations
import argparse
import sys
import threading
import webbrowser
from pathlib import Path


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("SiteCare needs Python 3.11 or newer. Python 3.13 is recommended.")
    parser = argparse.ArgumentParser(description="SiteCare local prototype")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--data-dir", type=Path, help="Advanced: separate local data folder")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("Choose a port between 1024 and 65535.")
    try:
        import uvicorn
        from sitecare.app import create_app
    except ImportError as exc:
        raise SystemExit("A package is missing. Run: python -m pip install -r requirements.txt\n" + str(exc)) from None
    app = create_app(args.data_dir)
    url = f"http://127.0.0.1:{args.port}"
    print(f"\nSiteCare prototype | {url}\nLocal data: {app.state.data_dir}\n"
          "Use synthetic/de-identified data only. Not validated for clinical use.\n"
          "Keep this window open. Press Ctrl+C to stop.\n")
    if not args.no_browser:
        timer = threading.Timer(1.4, lambda: webbrowser.open(url))
        timer.daemon = True
        timer.start()
    # Loopback only: intentionally no option to expose this prototype to the LAN.
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False,
                log_level="warning", proxy_headers=False, server_header=False)


if __name__ == "__main__":
    main()
