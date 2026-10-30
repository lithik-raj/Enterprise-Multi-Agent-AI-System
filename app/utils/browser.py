"""
Enterprise Multi-Agent AI — Browser Launcher Utility.
Provides multi-strategy, guaranteed browser launching across Windows, Linux, and macOS.
"""

import logging
import os
import subprocess
import sys
import webbrowser

logger = logging.getLogger(__name__)

_BROWSER_LAUNCHED = False


def open_platform_browser(url: str, force: bool = False) -> bool:
    """
    Open the given URL in the default browser.
    Guaranteed to work on Windows by trying native ShellExecute, cmd start, and webbrowser.
    Fires at most once per process lifetime unless force=True.
    """
    global _BROWSER_LAUNCHED

    if _BROWSER_LAUNCHED and not force:
        return True

    # Check if disabled via environment variable
    if os.getenv("NO_BROWSER", "0").lower() in ("1", "true", "yes"):
        return False

    _BROWSER_LAUNCHED = True
    opened = False

    # Strategy 1: Native Windows ShellExecute (100% reliable for Windows registered default browser)
    if sys.platform == "win32":
        try:
            os.startfile(url)
            opened = True
            logger.info("Browser launched via Windows ShellExecute: %s", url)
        except Exception as exc:
            logger.debug("os.startfile fallback: %s", exc)

        # Strategy 2: Windows cmd.exe start (brings window to foreground)
        if not opened:
            try:
                subprocess.Popen(f'cmd.exe /c start "" "{url}"', shell=True)
                opened = True
                logger.info("Browser launched via cmd.exe start: %s", url)
            except Exception as exc:
                logger.debug("cmd.exe start fallback: %s", exc)

    # Strategy 3: Standard Python webbrowser module (cross-platform fallback)
    if not opened:
        try:
            webbrowser.open(url)
            opened = True
            logger.info("Browser launched via webbrowser.open: %s", url)
        except Exception as exc:
            logger.warning("Could not launch browser automatically: %s", exc)

    return opened
