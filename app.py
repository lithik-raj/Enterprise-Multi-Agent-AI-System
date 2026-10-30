"""
Enterprise Multi-Agent AI Platform — Application Entry Point.
Clean, quiet launcher that automatically opens the web platform in the browser.

Usage:
    python app.py
    python run.py
"""

import os
import sys
import time
import socket
import threading
import urllib.request
import uvicorn
from app.config import get_settings

# Ensure safe UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

settings = get_settings()


def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check whether a TCP socket port is actively bound without throwing timeouts."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def _is_app_healthy(url: str, timeout: float = 0.8) -> bool:
    """Check whether the platform is responding with HTTP 200 on /api/health."""
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _wait_and_open_browser(target_url: str, max_wait: float = 25.0):
    """
    Polls /api/health until ready, then launches the browser cleanly.
    Guaranteed to avoid premature load errors and catch all exceptions.
    """
    from app.utils.browser import open_platform_browser

    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            if _is_app_healthy(target_url, timeout=0.6):
                time.sleep(0.1)
                open_platform_browser(target_url)
                return
        except Exception:
            pass
        time.sleep(0.15)

    # Fallback attempt if timeout reached
    try:
        open_platform_browser(target_url)
    except Exception:
        pass


def print_clean_banner(url: str):
    """Clean, clutter-free startup message as requested by the user."""
    banner = f"""
======================================================================
  Enterprise Multi-Agent AI Platform
  URL: {url}
  Opening browser automatically...
  (Press CTRL+C in this terminal to stop the server)
======================================================================
"""
    print(banner.strip() + "\n", flush=True)


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    requested_port = int(os.getenv("PORT", "8000"))
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{display_host}:{requested_port}"

    # If already running and healthy, open browser instantly and exit quietly
    if _is_port_in_use(requested_port, display_host):
        if _is_app_healthy(url, timeout=0.8):
            print_clean_banner(url)
            if os.getenv("NO_BROWSER", "0").lower() not in ("1", "true"):
                from app.utils.browser import open_platform_browser
                open_platform_browser(url, force=True)
            sys.exit(0)
        else:
            # Pick next free port if occupied by dead/foreign process
            for candidate in range(requested_port + 1, requested_port + 20):
                if not _is_port_in_use(candidate, display_host):
                    requested_port = candidate
                    url = f"http://{display_host}:{requested_port}"
                    break

    port = requested_port
    print_clean_banner(url)

    # Launch browser only once server is verified ready
    if os.getenv("NO_BROWSER", "0").lower() not in ("1", "true"):
        threading.Thread(target=_wait_and_open_browser, args=(url,), daemon=True).start()

    # Run Uvicorn with clean log level to suppress unwanted info logs
    log_level = os.getenv("LOG_LEVEL", "warning").lower()

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=settings.DEBUG,
            log_level=log_level,
        )
    except KeyboardInterrupt:
        print("\n[*] Server stopped. Goodbye!\n", flush=True)
    except Exception as exc:
        print(f"\n[!] Server error: {exc}", flush=True)
        sys.exit(1)
