import re
import unittest
from datetime import timedelta

from time_utils import moscow_backup_timestamp, moscow_iso_now, moscow_now, moscow_today


class MoscowTimeTests(unittest.TestCase):
    def test_moscow_timezone_is_utc_plus_three(self):
        self.assertEqual(moscow_now().utcoffset(), timedelta(hours=3))

    def test_display_time_keeps_existing_format(self):
        self.assertRegex(moscow_iso_now(), r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")

    def test_date_and_backup_formats(self):
        self.assertRegex(moscow_today(), r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(
            moscow_backup_timestamp(),
            r"^\d{8}_\d{6}_\d{6}$",
        )


if __name__ == "__main__":
    unittest.main()
