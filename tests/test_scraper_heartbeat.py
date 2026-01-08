
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from scraper_utils import Heartbeat

# Mocking scraper.py's main loop structure
async def mock_scraper_loop(timeout=0.5):
    """
    Simulates the main scraper loop.
    Ideally, we would import the actual scraper, but it's often a script not a module.
    We'll test if we can wrap a long running async operation with Heartbeat.
    """
    with Heartbeat(interval=0.1, message="Scraper is alive..."):
        await asyncio.sleep(timeout)

class TestScraperHeartbeat(unittest.TestCase):
    @patch('scraper_utils.logger')
    def test_scraper_loop_has_heartbeat(self, mock_logger):
        # Run the mock loop
        asyncio.run(mock_scraper_loop(timeout=0.3))
        
        # Check if logger was called with the heartbeat message
        # We expect at least 2 calls (initial start + 2 intervals of 0.1s in 0.3s)
        self.assertGreaterEqual(mock_logger.info.call_count, 2)
        mock_logger.info.assert_called_with("Scraper is alive...")

if __name__ == '__main__':
    unittest.main()
