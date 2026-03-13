"""Entry point for the Alteryx Git Companion app.

Responsibilities:
- Port probe: find the first available port in 7433–7443 range.
- Uvicorn programmatic start: pass the pre-bound socket to avoid race condition.
- Browser open: schedule webbrowser.open() 1 second after server starts.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import socket
import threading
import webbrowser

import uvicorn

from app.server import app as fastapi_app


def find_available_port(
    start: int = 7433, count: int = 11
) -> tuple[int, socket.socket]:
    """Return (port, bound_socket) for the first available port in the range.

    The caller MUST pass the returned socket to uvicorn.Config to avoid a race
    condition between probing and binding.

    Args:
        start: First port to try (default 7433).
        count: Number of ports to probe (default 11, covering 7433–7443).

    Raises:
        OSError: If all ports in the range are already in use.
    """
    for port in range(start, start + count):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return port, sock
        except OSError:
            sock.close()
    raise OSError(
        f"All ports {start}–{start + count - 1} are in use. "
        "Close another instance of Alteryx Git Companion and try again."
    )


def main() -> None:
    """Start the FastAPI server and open the browser."""
    port, sock = find_available_port()
    print(f"Alteryx Git Companion running at http://localhost:{port}")

    # Schedule browser open 1 second after server starts listening
    timer = threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}"))
    timer.daemon = True
    timer.start()

    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve(sockets=[sock]))


if __name__ == "__main__":
    # freeze_support() MUST be first — prevents infinite spawn on Windows onefile
    multiprocessing.freeze_support()
    main()
