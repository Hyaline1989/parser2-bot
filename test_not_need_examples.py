import tempfile
import unittest
from pathlib import Path

import app as app_module


class NotNeedExamplesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_drafts_file = app_module.DRAFTS_FILE
        self.original_examples_file = app_module.NOT_NEED_EXAMPLES_FILE
        app_module.DRAFTS_FILE = Path(self.temp_dir.name) / "drafts.json"
        app_module.NOT_NEED_EXAMPLES_FILE = Path(self.temp_dir.name) / "not_need.json"
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.DRAFTS_FILE = self.original_drafts_file
        app_module.NOT_NEED_EXAMPLES_FILE = self.original_examples_file
        self.temp_dir.cleanup()

    def test_mark_not_need_saves_source_message_and_removes_draft(self):
        app_module.write_saved_drafts(
            [
                {
                    "message_key": "max|1|2",
                    "source": "MAX: Тестовый чат #2",
                    "source_object": "Тестовый объект",
                    "status": "черновик",
                    "max": {"text": "Сможем принять 10 человек?"},
                    "rows": [{"object": "Тестовый объект", "total": 10}],
                }
            ]
        )

        response = self.client.post(
            "/mark-not-need", json={"index": 0, "message_key": "max|1|2"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(app_module.load_saved_drafts(), [])
        examples = app_module.load_not_need_examples()
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["message"], "Сможем принять 10 человек?")
        self.assertEqual(examples[0]["source_object"], "Тестовый объект")

    def test_published_draft_cannot_be_marked_not_need(self):
        app_module.write_saved_drafts(
            [{"message_key": "published", "status": "опубликовано", "rows": []}]
        )

        response = self.client.post(
            "/mark-not-need", json={"index": 0, "message_key": "published"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(app_module.load_saved_drafts()), 1)
        self.assertEqual(app_module.load_not_need_examples(), [])


if __name__ == "__main__":
    unittest.main()
