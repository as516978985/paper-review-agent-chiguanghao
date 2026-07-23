import unittest

from app.config import settings
from app.docx_tools import extract_text, inspect_document
from app.memory import identify_document


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = settings.static_dir.parent / "resources" / "论文初稿.docx"
        cls.data = cls.path.read_bytes()

    def test_extract_text(self):
        text = extract_text(self.data)
        self.assertIn("作者编号：2026230417", text)
        self.assertIn("参考文献", text)

    def test_format_check(self):
        result = inspect_document(self.data, settings.format_policy)
        self.assertGreater(result["summary"]["total"], 10)
        self.assertGreater(result["summary"]["fail"], 0)

    def test_identity_stays_stable_after_body_change(self):
        text = extract_text(self.data)
        first = identify_document(text)
        second = identify_document(text.replace("核心流程验证", "完整流程验证"))
        self.assertTrue(first.rememberable)
        self.assertEqual(first.author_key, second.author_key)
        self.assertEqual(first.paper_key, second.paper_key)
        self.assertNotEqual(first.document_hash, second.document_hash)


if __name__ == "__main__":
    unittest.main()