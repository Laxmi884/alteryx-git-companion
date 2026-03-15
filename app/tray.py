"""System tray icon stub for Phase 15.

Provides start_tray() which will be fully implemented in Plan 03 with pystray.
This stub allows app/main.py to import and call start_tray() without error
while Plan 02 tests run; Plan 03 will replace the body with the real pystray
integration.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def start_tray(port: int, server: object) -> None:  # noqa: ARG001
    """Start the system tray icon (stub — implemented in Plan 03).

    Args:
        port: The port uvicorn is listening on.
        server: The uvicorn.Server instance (used for graceful quit in Plan 03).
    """
    logger.debug("start_tray called (stub — Plan 03 will implement pystray icon)")
