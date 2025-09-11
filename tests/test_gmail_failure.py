import unittest
from unittest.mock import Mock

from data_pipeline.gmail_utils import send_message


class TestGmailFailure(unittest.TestCase):
    def test_send_failure(self):
        mock_service = Mock()
        mock_service.users.return_value.messages.return_value.send.side_effect = Exception(
            "Send fail!")
        # Should return None, not crash
        result = send_message(mock_service, "me", {"raw": "test"})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
