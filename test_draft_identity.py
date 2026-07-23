import json
import tempfile
import unittest
from pathlib import Path

import app as app_module


class DraftIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_drafts_file = app_module.DRAFTS_FILE
        self.original_history_file = app_module.PUBLICATION_HISTORY_FILE
        app_module.DRAFTS_FILE = Path(self.temp_dir.name) / "drafts.json"
        app_module.PUBLICATION_HISTORY_FILE = Path(self.temp_dir.name) / "history.json"
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        app_module.write_saved_drafts(
            [
                {
                    "message_key": "first-key",
                    "status": "черновик",
                    "rows": [{"object": "Первый", "position": "Должность"}],
                },
                {
                    "message_key": "second-key",
                    "status": "черновик",
                    "rows": [{"object": "Второй", "position": "Должность"}],
                },
            ]
        )

    def tearDown(self):
        app_module.DRAFTS_FILE = self.original_drafts_file
        app_module.PUBLICATION_HISTORY_FILE = self.original_history_file
        self.temp_dir.cleanup()

    def test_stable_key_survives_index_shift_after_delete(self):
        delete_response = self.client.post(
            "/delete-draft",
            json={"index": 0, "message_key": "first-key"},
        )
        self.assertEqual(delete_response.status_code, 200)

        confirm_response = self.client.post(
            "/confirm-draft",
            json={"index": 1, "message_key": "second-key"},
        )
        self.assertEqual(confirm_response.status_code, 200)

        drafts = json.loads(app_module.DRAFTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["message_key"], "second-key")
        self.assertEqual(drafts[0]["status"], "подтверждён")

    def test_publish_uses_key_when_visible_index_is_stale(self):
        self.client.post(
            "/delete-draft",
            json={"index": 0, "message_key": "first-key"},
        )
        drafts = app_module.load_saved_drafts()
        drafts[0]["status"] = "подтверждён"
        app_module.write_saved_drafts(drafts)

        published_rows = []
        original_publish = app_module.publish_vector_rows

        def fake_publish(rows):
            published_rows.extend(rows)
            return {"changes": [], "errors": [], "backup_path": "test-backup.db"}

        app_module.publish_vector_rows = fake_publish
        try:
            response = self.client.post(
                "/publish-draft-to-vector",
                json={"index": 1, "message_key": "second-key"},
            )
        finally:
            app_module.publish_vector_rows = original_publish

        self.assertEqual(response.status_code, 200)
        self.assertEqual(published_rows[0]["object"], "Второй")


if __name__ == "__main__":
    unittest.main()
