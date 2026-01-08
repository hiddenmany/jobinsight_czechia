
import time
import io
import sys
import unittest
from unittest.mock import patch, MagicMock
from scraper_utils import Heartbeat, logger

class TestHeartbeat(unittest.TestCase):
    @patch('scraper_utils.logger')
    def test_heartbeat_prints_periodically(self, mock_logger):
        # Initialize heartbeat with a very short interval for testing
        hb = Heartbeat(interval=0.1)
        
        # Start heartbeat
        hb.start()
        
        # Wait for enough time for at least 2 beats
        time.sleep(0.25)
        
        # Stop heartbeat
        hb.stop()
        
        # Check if logger.info was called
        # We expect at least 2 calls
        self.assertGreaterEqual(mock_logger.info.call_count, 2)
        # Verify the message
        mock_logger.info.assert_called_with("Heartbeat: Process is still active...")

    @patch('scraper_utils.logger')
    def test_heartbeat_context_manager(self, mock_logger):
        # Test usage as context manager
        with Heartbeat(interval=0.1):
            time.sleep(0.25)
            
        self.assertGreaterEqual(mock_logger.info.call_count, 2)
        mock_logger.info.assert_called_with("Heartbeat: Process is still active...")

if __name__ == '__main__':
    unittest.main()
