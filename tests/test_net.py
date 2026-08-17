import unittest

from lanmic.net import _is_usable, lan_ips, phone_urls


class NetTests(unittest.TestCase):
    def test_rejects_loopback_and_link_local(self):
        self.assertFalse(_is_usable("127.0.0.1"))
        self.assertFalse(_is_usable("0.0.0.0"))
        self.assertFalse(_is_usable("169.254.10.20"))
        self.assertFalse(_is_usable("not-an-ip"))

    def test_accepts_rfc1918(self):
        self.assertTrue(_is_usable("192.168.1.8"))
        self.assertTrue(_is_usable("10.0.0.2"))
        self.assertTrue(_is_usable("172.16.5.4"))

    def test_lan_ips_are_usable(self):
        for ip in lan_ips():
            self.assertTrue(_is_usable(ip), ip)

    def test_phone_urls(self):
        urls = phone_urls(8443, "https")
        for u in urls:
            self.assertTrue(u.startswith("https://"))
            self.assertIn(":8443/", u)


if __name__ == "__main__":
    unittest.main()
