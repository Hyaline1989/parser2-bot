import tempfile
import unittest
from pathlib import Path

import app as app_module


class BulkDeletePublishedTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_drafts_file = app_module.DRAFTS_FILE
        self.original_history_file = app_module.PUBLICATION_HISTORY_FILE
        app_module.DRAFTS_FILE = Path(self.temp_dir.name) / "drafts.json"
        app_module.PUBLICATION_HISTORY_FILE = Path(self.temp_dir.name) / "history.json"
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.DRAFTS_FILE = self.original_drafts_file
        app_module.PUBLICATION_HISTORY_FILE = self.original_history_file
        self.temp_dir.cleanup()

    def test_only_published_drafts_are_deleted(self):
        app_module.write_saved_drafts(
            [
                {"message_key": "published-1", "status": "опубликовано", "rows": [{}]},
                {"message_key": "confirmed-1", "status": "подтверждён", "rows": [{}]},
                {"message_key": "draft-1", "status": "черновик", "rows": [{}]},
                {"message_key": "published-2", "status": "опубликовано", "rows": [{}]},
            ]
        )
        app_module.PUBLICATION_HISTORY_FILE.write_text(
            '[{"id": "history-entry"}]', encoding="utf-8"
        )

        response = self.client.post("/delete-published-drafts")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["deleted_count"], 2)
        remaining = app_module.load_saved_drafts()
        self.assertEqual(
            [draft["message_key"] for draft in remaining],
            ["confirmed-1", "draft-1"],
        )
        self.assertTrue(app_module.PUBLICATION_HISTORY_FILE.exists())


if __name__ == "__main__":
    unittest.main()
