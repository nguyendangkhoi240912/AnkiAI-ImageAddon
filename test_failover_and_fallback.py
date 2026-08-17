import sys, json, types, threading, unittest
from unittest.mock import MagicMock

for name in ["aqt","aqt.mw","aqt.utils","anki","anki.hooks","PyQt6","PyQt5","PyQt6.QtWidgets","PyQt5.QtWidgets"]:
    sys.modules.setdefault(name, types.ModuleType(name))

sys.path.insert(0, "/Users/nguyenkhanh/Desktop/AnkiAI-ImageAddon/AnkiAI_ImageAddon")

def make_response(status_code, body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body or {}
    r.text = json.dumps(body or {})
    return r

class TestResolveUrl(unittest.TestCase):
    def test_empty_is_ultra(self):
        from modules.imagen_provider import resolve_imagen_predict_url
        url = resolve_imagen_predict_url("")
        self.assertIn("ultra", url)
        self.assertIn(":predict", url)
    def test_passthrough(self):
        from modules.imagen_provider import resolve_imagen_predict_url
        u = "https://example.com/v1/models/custom:predict"
        self.assertEqual(resolve_imagen_predict_url(u), u)
    def test_generatecontent_converted(self):
        from modules.imagen_provider import resolve_imagen_predict_url
        url = resolve_imagen_predict_url("https://x.com/v1/models/imagen-4.0-ultra-generate-001:generateContent")
        self.assertIn(":predict", url)
        self.assertNotIn("generateContent", url)

class TestImagenFailover(unittest.TestCase):
    def _p(self, ms):
        from modules.imagen_provider import ImagenProvider, resolve_imagen_predict_url
        p = ImagenProvider.__new__(ImagenProvider)
        p.api_key="K"; p.service_account_json=""; p.timeout=5; p.max_concurrent=1
        p.retries=3; p.enable_safety=True; p.model="imagen-4.0-ultra-generate-001"
        p.endpoint=resolve_imagen_predict_url(""); p.request_count=0; p.success_count=0
        p.failure_count=0; p.total_cost_usd=0.0; p.lock=threading.Lock(); p.session=ms
        return p
    def test_ultra_to_standard(self):
        ms = MagicMock()
        ms.post.side_effect=[make_response(404,{"error":{"message":"nf"}}),make_response(200,{"predictions":[{"bytesBase64Encoded":"aGVsbG8="}]})]
        p=self._p(ms); imgs=p.generate_image("cat",1024,1024)
        self.assertEqual(len(imgs),1); self.assertIn("imagen-4.0-generate-001",p.model)
    def test_ultra_standard_to_3(self):
        ms=MagicMock()
        ms.post.side_effect=[make_response(404,{"error":{"message":"nf"}}),make_response(403,{"error":{"message":"fb"}}),make_response(200,{"predictions":[{"bytesBase64Encoded":"aGVsbG8="}]})]
        p=self._p(ms); imgs=p.generate_image("dog",1024,1024)
        self.assertEqual(len(imgs),1); self.assertIn("imagen-3.0",p.model)
    def test_all_fail_raises(self):
        from modules.imagen_provider import ImageProviderError
        ms=MagicMock(); ms.post.return_value=make_response(400,{"error":{"message":"all"}})
        p=self._p(ms)
        with self.assertRaises(ImageProviderError): p.generate_image("x",1024,1024)

class TestGeminiDescriberNoModelDowngrade(unittest.TestCase):
    """Gemini describer stays on gemini-3.5-flash-lite; on 400/403/404 it
    skips to next API key instead of switching models."""
    def _d(self, ms):
        from modules.imagen_provider import GeminiImageDescriber
        d=GeminiImageDescriber.__new__(GeminiImageDescriber)
        d.api_keys=["K1","K2"]; d.model="gemini-3.5-flash-lite"
        d.base_url="https://generativelanguage.googleapis.com/v1beta/models"
        d.timeout=5; d.cache={}; d.lock=threading.Lock(); d.session=ms
        return d

    def test_stays_on_flash_lite_after_404(self):
        # Key1 -> 404, Key2 -> 200: model must remain gemini-3.5-flash-lite
        success = {"candidates":[{"content":{"parts":[{"text":"A scene."}]}}]}
        ms=MagicMock()
        ms.post.side_effect=[make_response(404,{"error":{"message":"not found"}}),make_response(200,success)]
        d=self._d(ms); r=d.generate_image_description("serendipity","happy accident","")
        self.assertEqual(r,"A scene.")
        self.assertEqual(d.model,"gemini-3.5-flash-lite")

    def test_never_uses_1_5_flash(self):
        # Even if both keys get 404, model should still be gemini-3.5-flash-lite
        from modules.imagen_provider import ImageProviderError
        ms=MagicMock(); ms.post.return_value=make_response(404,{"error":{"message":"nf"}})
        d=self._d(ms)
        with self.assertRaises(ImageProviderError):
            d.generate_image_description("test","def","")
        self.assertEqual(d.model,"gemini-3.5-flash-lite")

    def test_all_keys_fail_raises(self):
        from modules.imagen_provider import ImageProviderError
        ms=MagicMock(); ms.post.return_value=make_response(400,{"error":{"message":"bad"}})
        d=self._d(ms)
        with self.assertRaises(ImageProviderError): d.generate_image_description("t","d","")

class TestConfigDefaults(unittest.TestCase):
    def test_json_is_ultra(self):
        with open("/Users/nguyenkhanh/Desktop/AnkiAI-ImageAddon/AnkiAI_ImageAddon/config.json") as f: cfg=json.load(f)
        self.assertIn("ultra", cfg.get("imagen_endpoint",""))
    def test_py_is_ultra(self):
        import re
        with open("/Users/nguyenkhanh/Desktop/AnkiAI-ImageAddon/AnkiAI_ImageAddon/modules/config.py") as f: src=f.read()
        m=re.search(r'"imagen_endpoint"\s*:\s*"([^"]+)"', src)
        self.assertIsNotNone(m); self.assertIn("ultra", m.group(1))

if __name__=="__main__":
    unittest.main(verbosity=2)
