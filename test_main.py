import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Adjust path to import main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import main

class TestTodaySpecialBot(unittest.TestCase):

    def test_is_indian_context_matches(self):
        # Should match Indian names, places, events
        self.assertTrue(main.is_indian_context("Swami Vivekananda was an Indian monk."))
        self.assertTrue(main.is_indian_context("The Indian Independence Act 1947 was passed."))
        self.assertTrue(main.is_indian_context("Gulzarilal Nanda was born in Punjab."))
        self.assertTrue(main.is_indian_context("Alluri Sitarama Raju led the Rampa Rebellion."))
        self.assertTrue(main.is_indian_context("Amol Rajan, Indian-English journalist."))

    def test_is_indian_context_exclusions(self):
        # Should exclude non-Indian matches with exclusion words
        self.assertFalse(main.is_indian_context("Zhuo Yanming, Chinese Buddhist monk and emperor"))
        self.assertFalse(main.is_indian_context("Patrick Roy, Canadian ice hockey player"))
        self.assertFalse(main.is_indian_context("Japanese Buddhist Zen master Dogen was born."))

    @patch('main.http_session.get')
    def test_fetch_wikipedia_events_mock(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [{"text": "Independence Day", "year": "1947"}]
        }
        mock_get.return_value = mock_response

        data = main.fetch_wikipedia_events("07", "04")
        self.assertIsNotNone(data)
        self.assertEqual(data["events"][0]["text"], "Independence Day")
        mock_get.assert_called_once()

if __name__ == "__main__":
    unittest.main()
