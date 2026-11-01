"""
S&P 500 Quantitative Valuation & Forensic Terminal — Local Desktop & Web Server App
===================================================================================
Launches the interactive workstation in a dedicated frameless desktop app window
(via Microsoft Edge / Google Chrome --app mode) and powers the in-app "Run Screener"
live progress bar and audit stream.
"""

import html
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "sp500_tierlist_dashboard.html")

SCAN_LOCK = threading.Lock()
SCAN_STATE = {
    "running": False,
    "stage": "idle",
    "completed": 0,
    "total": 0,
    "ticker": "",
    "status": "",
    "clean_count": 0,
    "flagged_count": 0,
    "insider_count": 0,
    "start_time": 0.0,
    "elapsed_sec": 0,
    "recent_logs": [],
}
LATEST_PAYLOAD = None


def load_payload_from_html():
    """Extracts the embedded PAYLOAD JSON from sp500_tierlist_dashboard.html if available."""
    global LATEST_PAYLOAD
    if LATEST_PAYLOAD is not None:
        return LATEST_PAYLOAD
    if not os.path.exists(HTML_PATH):
        return {"stocks": [], "cohorts": [], "watchlists": []}
    try:
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if "PAYLOAD = {" in line:
                    raw = line.split("PAYLOAD = ", 1)[1].strip().rstrip(";")
                    LATEST_PAYLOAD = json.loads(raw)
                    if "watchlists" not in LATEST_PAYLOAD:
                        LATEST_PAYLOAD["watchlists"] = []
                    return LATEST_PAYLOAD
    except Exception:
        pass
    return {"stocks": [], "cohorts": [], "watchlists": []}


def _on_scan_progress(info):
    with SCAN_LOCK:
        SCAN_STATE["stage"] = info.get("stage", "scanning")
        SCAN_STATE["completed"] = info.get("completed", 0)
        SCAN_STATE["total"] = info.get("total", 0)
        SCAN_STATE["ticker"] = info.get("ticker", "")
        SCAN_STATE["status"] = info.get("status", "")
        SCAN_STATE["clean_count"] = info.get("clean_count", 0)
        SCAN_STATE["flagged_count"] = info.get("flagged_count", 0)
        SCAN_STATE["insider_count"] = info.get("insider_count", 0)
        if SCAN_STATE["start_time"] > 0:
            SCAN_STATE["elapsed_sec"] = int(time.time() - SCAN_STATE["start_time"])

        sym = info.get("ticker", "")
        st = info.get("status", "")
        comp = info.get("completed", 0)
        tot = info.get("total", 0)
        if sym and st:
            safe_st = html.escape(str(st))
            if "RED FLAG" in st:
                color = "#f87171"
            elif "Score:" in st:
                color = "#34d399"
            else:
                color = "#94a3b8"
            line = (
                f'<span style="color:#64748b;">[{comp:3d}/{tot}]</span> '
                f'<strong style="color:#f8fafc;">{html.escape(sym):5}</strong> '
                f'&rarr; <span style="color:{color};">{safe_st}</span>'
            )
            SCAN_STATE["recent_logs"].append(line)
            if len(SCAN_STATE["recent_logs"]) > 40:
                SCAN_STATE["recent_logs"] = SCAN_STATE["recent_logs"][-40:]


def _run_scan_worker(max_stocks=None, mode="full_universe", custom_tickers=None):
    global LATEST_PAYLOAD
    try:
        import importlib
        import research_agent
        import dashboard_builder
        import sp500_peg_screener
        importlib.reload(research_agent)
        importlib.reload(dashboard_builder)
        importlib.reload(sp500_peg_screener)

        payload = sp500_peg_screener.run_screener(
            max_stocks=max_stocks,
            progress_callback=_on_scan_progress,
            mode=mode,
            custom_tickers=custom_tickers,
        )
        if payload:
            LATEST_PAYLOAD = payload
        with SCAN_LOCK:
            SCAN_STATE["running"] = False
            SCAN_STATE["stage"] = "done"
            SCAN_STATE["elapsed_sec"] = int(time.time() - SCAN_STATE["start_time"])
    except Exception as exc:
        with SCAN_LOCK:
            SCAN_STATE["running"] = False
            SCAN_STATE["stage"] = "error"
            SCAN_STATE["recent_logs"].append(
                f'<span style="color:#f87171;">Error during scan: {html.escape(str(exc))}</span>'
            )


class TerminalRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Silence per-poll HTTP log spam in terminal
        pass

    def _send_json(self, data, status=200):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/sp500_tierlist_dashboard.html"):
            if not os.path.exists(HTML_PATH):
                msg = b"<h2>Dashboard HTML not found. Run a scan first.</h2>"
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(msg)
                return
            with open(HTML_PATH, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/scan/status":
            with SCAN_LOCK:
                if SCAN_STATE["running"] and SCAN_STATE["start_time"] > 0:
                    SCAN_STATE["elapsed_sec"] = int(time.time() - SCAN_STATE["start_time"])
                snapshot = dict(SCAN_STATE)
                snapshot["recent_logs"] = list(SCAN_STATE["recent_logs"])
            self._send_json(snapshot)
            return

        if path == "/api/payload":
            self._send_json(load_payload_from_html())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        global LATEST_PAYLOAD
        path = self.path.split("?", 1)[0]
        if path == "/api/scan/start":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                req = json.loads(body.decode("utf-8"))
            except Exception:
                req = {}
            max_stocks = req.get("max_stocks", None)
            mode = req.get("mode", "full_universe")
            custom_tickers = req.get("custom_tickers", None)
            if isinstance(custom_tickers, list):
                custom_tickers = [str(t).strip().upper() for t in custom_tickers if str(t).strip()]
            else:
                custom_tickers = None

            est_total = len(custom_tickers) if custom_tickers else (max_stocks or 503)

            with SCAN_LOCK:
                if SCAN_STATE["running"]:
                    self._send_json({"ok": True, "already_running": True})
                    return
                SCAN_STATE.update({
                    "running": True,
                    "stage": "scanning",
                    "completed": 0,
                    "total": est_total,
                    "ticker": "INIT",
                    "status": "Initializing scan...",
                    "clean_count": 0,
                    "flagged_count": 0,
                    "insider_count": 0,
                    "start_time": time.time(),
                    "elapsed_sec": 0,
                    "recent_logs": [],
                })

            t = threading.Thread(
                target=_run_scan_worker,
                args=(max_stocks, mode, custom_tickers),
                daemon=True,
            )
            t.start()
            self._send_json({"ok": True, "started": True})
            return

        if path == "/api/watchlists":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                req = json.loads(body.decode("utf-8"))
            except Exception:
                req = {}
            raw_wls = req.get("watchlists", [])
            clean_wls = []
            if isinstance(raw_wls, list):
                for idx, wl in enumerate(raw_wls):
                    if not isinstance(wl, dict):
                        continue
                    wid = str(wl.get("id") or f"wl_{idx + 1}").strip()
                    wname = str(wl.get("name") or "Watchlist").strip()[:48]
                    wtickers = []
                    seen_t = set()
                    for t in (wl.get("tickers") or []):
                        ts = str(t).strip().upper()
                        if ts and ts not in seen_t:
                            seen_t.add(ts)
                            wtickers.append(ts)
                    clean_wls.append({"id": wid, "name": wname, "tickers": wtickers})

            payload = load_payload_from_html()
            payload["watchlists"] = clean_wls
            LATEST_PAYLOAD = payload
            try:
                import sp500_peg_screener
                sp500_peg_screener.save_database_to_disk(
                    payload.get("stocks", []),
                    payload.get("cohorts", []),
                    clean_wls,
                )
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
                return

            self._send_json({"ok": True, "watchlists": clean_wls})
            return

        if path == "/api/audit/ticker":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                req = json.loads(body.decode("utf-8"))
            except Exception:
                req = {}
            ticker = str(req.get("ticker", "")).strip().upper()
            if not ticker:
                self._send_json({"ok": False, "error": "No ticker symbol provided."}, status=400)
                return

            print(f"[*] Running Live Single-Ticker Forensic Audit on {ticker}...", flush=True)
            try:
                import importlib
                import research_agent
                import dashboard_builder
                import sp500_peg_screener
                importlib.reload(research_agent)
                importlib.reload(dashboard_builder)
                importlib.reload(sp500_peg_screener)

                stock = sp500_peg_screener.audit_single_ticker_live(ticker)
                if not stock:
                    err = getattr(sp500_peg_screener, 'get_last_ticker_error', lambda x: None)(ticker)
                    err_msg = f"Audit failed for {ticker}: {err}" if err else f"Ticker '{ticker}' was not found on Yahoo Finance or has no market data."
                    self._send_json(
                        {"ok": False, "error": err_msg},
                        status=404,
                    )
                    return

                payload = load_payload_from_html()
                stocks_list = payload.get("stocks", [])
                updated = False
                for i, existing in enumerate(stocks_list):
                    if existing.get("ticker", "").upper() == stock["ticker"].upper():
                        # Preserve existing valid company name and sector if Yahoo omitted them
                        if stock.get("company") in (stock["ticker"], "", None) and existing.get("company"):
                            stock["company"] = existing["company"]
                        if stock.get("sector") in ("Financials/Other", "", None) and existing.get("sector"):
                            stock["sector"] = existing["sector"]
                        stocks_list[i] = stock
                        updated = True
                        break
                if not updated:
                    stocks_list.append(stock)

                sp500_peg_screener.assign_tiers_and_basket(stocks_list)
                stocks_list.sort(key=lambda x: (x.get("in_basket", False), x.get("composite_score", 0)), reverse=True)
                payload["stocks"] = stocks_list
                LATEST_PAYLOAD = payload
                try:
                    sp500_peg_screener.save_database_to_disk(
                        stocks_list,
                        payload.get("cohorts", []),
                        payload.get("watchlists", []),
                    )
                except Exception:
                    pass

                print(
                    f"    [Single Audit OK] {stock['ticker']:5} -> Tier {stock['tier']} | "
                    f"Score: {stock['composite_score']:.1f}/100 | "
                    f"Database Size: {len(stocks_list)} stocks | "
                    f"Verdict: {(stock.get('research') or {}).get('verdict', 'N/A')}",
                    flush=True,
                )
                self._send_json({"ok": True, "stock": stock, "stocks": stocks_list, "watchlists": payload.get("watchlists", [])})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
            return

        self.send_response(404)
        self.end_headers()


def find_free_port(preferred=8765):
    for port in range(preferred, preferred + 25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def launch_desktop_window(url):
    """Attempts to launch Edge or Chrome in native frameless --app mode on Windows."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, f"--app={url}", "--window-size=1480,940"])
                return True
            except Exception:
                pass
    webbrowser.open(url)
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="S&P 500 Forensic Terminal Web & Desktop Server")
    parser.add_argument("--host", default=None, help="Host address to bind to (e.g. 0.0.0.0 or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (default: $PORT or 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not launch desktop window on startup")
    args, _ = parser.parse_known_args()

    env_port = os.environ.get("PORT") or os.environ.get("HTTP_PLATFORM_PORT")
    env_host = os.environ.get("HOST")

    is_cloud = bool(env_port or env_host or os.environ.get("RENDER") or os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("FLY_APP_NAME"))
    
    if args.port:
        port = args.port
    elif env_port:
        port = int(env_port)
    else:
        port = find_free_port(8765)

    if args.host:
        host = args.host
    elif env_host:
        host = env_host
    elif is_cloud:
        host = "0.0.0.0"
    else:
        host = "127.0.0.1"

    url = f"http://{host}:{port}"
    server = ThreadingHTTPServer((host, port), TerminalRequestHandler)

    print("=" * 76)
    print(" S&P 500 QUANTITATIVE VALUATION & FORENSIC TERMINAL (APP SERVER)")
    print("=" * 76)
    print(f" Environment   : {'Cloud Web Service' if is_cloud else 'Local Desktop Workstation'}")
    print(f" Listening On  : http://{host}:{port}")
    if is_cloud:
        print(f" Public Access : Accessible via your cloud domain / IP on port {port}")
    else:
        print(f" Local App URL : http://127.0.0.1:{port}")
    print(" Live Scanner  : Ready (Click 'Run Screener' in the app header)")
    print(" To Stop Server: Press Ctrl+C")
    print("=" * 76)

    # Launch desktop frameless window only when running locally on Windows and not in cloud/headless mode
    if not is_cloud and not args.no_browser and os.name == "nt":
        threading.Timer(0.4, lambda: launch_desktop_window(f"http://127.0.0.1:{port}")).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down terminal server...")
        server.server_close()


if __name__ == "__main__":
    main()
