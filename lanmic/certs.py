"""Create a reusable self-signed cert covering localhost and current LAN IPs.

Phone browsers refuse getUserMedia on plain http://192.168.x.x.
A self-signed cert with those IPs in the SAN is the least-friction option
for a local-first tool: the user taps Through / Advanced once per install.
"""

from __future__ import annotations

import datetime
import ipaddress
import socket
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from lanmic.net import lan_ips
from lanmic.paths import user_data_dir


def cert_dir() -> Path:
    return user_data_dir()


def cert_paths() -> tuple[Path, Path]:
    folder = cert_dir()
    return folder / "cert.pem", folder / "key.pem"


def _load_cert(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def _san_values(cert: x509.Certificate) -> set[str]:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return set()
    values: set[str] = set()
    for name in san:
        values.add(str(name.value))
    return values


def needed_sans() -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    host = socket.gethostname().split(".")[0]
    if host:
        names.append(x509.DNSName(host))
    for ip in lan_ips():
        names.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
    # de-dup while preserving order
    seen: set[str] = set()
    unique: list[x509.GeneralName] = []
    for n in names:
        key = f"{type(n).__name__}:{n.value}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(n)
    return unique


def cert_covers_current_network(cert_path: Path) -> bool:
    if not cert_path.is_file():
        return False
    try:
        cert = _load_cert(cert_path)
    except ValueError:
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    if cert.not_valid_after_utc < now + datetime.timedelta(days=1):
        return False
    have = _san_values(cert)
    for ip in lan_ips():
        if ip not in have:
            return False
    return True


def ensure_certificate(force: bool = False) -> tuple[Path, Path]:
    folder = cert_dir()
    folder.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = cert_paths()
    if not force and cert_path.is_file() and key_path.is_file() and cert_covers_current_network(cert_path):
        return cert_path, key_path
    return generate_certificate(cert_path, key_path)


def generate_certificate(cert_path: Path, key_path: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LanMic"),
            x509.NameAttribute(NameOID.COMMON_NAME, "LanMic local"),
        ]
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    san = x509.SubjectAlternativeName(needed_sans())
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(san, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    try:
        cert_path.chmod(0o644)
        key_path.chmod(0o600)
    except OSError:
        pass
    return cert_path, key_path
