"""Enumerate LAN IPv4 addresses for QR codes and certificate SANs."""

from __future__ import annotations

import socket
from ipaddress import IPv4Address


def _is_usable(ip: str) -> bool:
    try:
        addr = IPv4Address(ip)
    except ValueError:
        return False
    if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_unspecified:
        return False
    if addr.is_reserved:
        return False
    return True


def default_route_ip() -> str | None:
    """IP of the interface that would be used to reach the internet."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
    except OSError:
        return None
    return ip if _is_usable(ip) else None


def lan_ips() -> list[str]:
    found: set[str] = set()
    primary = default_route_ip()
    if primary:
        found.add(primary)

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if _is_usable(ip):
                found.add(ip)
    except OSError:
        pass

    # Keep the default-route address first: that is usually the Wi-Fi NIC
    # the phone can actually reach.
    ordered = sorted(found)
    if primary in found:
        ordered.remove(primary)
        ordered.insert(0, primary)
    return ordered


def phone_urls(port: int, scheme: str = "https") -> list[str]:
    return [f"{scheme}://{ip}:{port}/" for ip in lan_ips()]
