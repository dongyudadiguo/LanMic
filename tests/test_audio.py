import unittest

try:
    from lanmic.audio import VIRTUAL_OUTPUT_HINTS, _norm, recording_hint, Device
    AUDIO_OK = True
except Exception as exc:  # pragma: no cover - env without extras
    AUDIO_OK = False
    AUDIO_ERR = exc


@unittest.skipUnless(AUDIO_OK, "sounddevice/numpy not installed")
class AudioHelperTests(unittest.TestCase):
    def _dev(self, name: str) -> Device:
        return Device(index=0, name=name, hostapi="Windows WASAPI",
                      max_input=0, max_output=2, default_samplerate=48000.0)

    def test_norm(self):
        self.assertEqual(_norm("CABLE Input (VB-Audio Virtual Cable)"),
                         "cable input vb-audio virtual cable")

    def test_hints_cover_vbcable(self):
        name = _norm("CABLE Input (VB-Audio Virtual Cable)")
        self.assertTrue(any(h in name for h in VIRTUAL_OUTPUT_HINTS))

    def test_recording_hint_for_cable(self):
        text = recording_hint(self._dev("CABLE Input (VB-Audio Virtual Cable)"))
        self.assertIn("CABLE Output", text)

    def test_recording_hint_speaker(self):
        self.assertIn("喇叭", recording_hint(None))


if __name__ == "__main__":
    unittest.main()
