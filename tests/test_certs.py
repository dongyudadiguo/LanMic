import tempfile
import unittest
from pathlib import Path

try:
    from cryptography import x509
    from lanmic.certs import generate_certificate, needed_sans
    CERT_OK = True
except Exception:
    CERT_OK = False


@unittest.skipUnless(CERT_OK, "cryptography not installed")
class CertTests(unittest.TestCase):
    def test_needed_sans_include_localhost(self):
        sans = needed_sans()
        values = {str(n.value) for n in sans}
        self.assertIn("localhost", values)
        self.assertIn("127.0.0.1", values)

    def test_generate_writes_pem(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            cert_path, key_path = generate_certificate(folder / "cert.pem", folder / "key.pem")
            self.assertTrue(cert_path.is_file())
            self.assertTrue(key_path.is_file())
            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            dns = [n.value for n in san if isinstance(n, x509.DNSName)]
            self.assertIn("localhost", dns)


if __name__ == "__main__":
    unittest.main()
