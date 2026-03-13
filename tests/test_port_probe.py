"""Unit tests for find_available_port() from app.main."""

from __future__ import annotations

import socket

import pytest
from app.main import find_available_port


def test_find_available_port_returns_7433():
    """When 7433 is free, find_available_port() returns (7433, socket)."""
    port, sock = find_available_port(start=7433, count=11)
    try:
        assert port == 7433
        assert isinstance(sock, socket.socket)
    finally:
        sock.close()


def test_find_available_port_skips_occupied():
    """When 7433 is bound by another socket, returns next free port (7434)."""
    # Pre-bind 7433 to simulate it being occupied
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 7433))
    try:
        port, sock = find_available_port(start=7433, count=11)
        try:
            assert port == 7434
            assert isinstance(sock, socket.socket)
        finally:
            sock.close()
    finally:
        blocker.close()


def test_find_available_port_raises_when_all_full():
    """When all ports 7433-7443 are bound, raises OSError."""
    blockers: list[socket.socket] = []
    try:
        for p in range(7433, 7444):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", p))
            blockers.append(s)

        with pytest.raises(OSError):
            find_available_port(start=7433, count=11)
    finally:
        for s in blockers:
            s.close()
