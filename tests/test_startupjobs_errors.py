
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from scraper import StartupJobsScraper

class TestStartupJobsErrors(unittest.TestCase):
    @patch('scraper.CORE')
    @patch('scraper.CIRCUIT_BREAKER')
    @patch('scraper.asyncio.sleep', new_callable=AsyncMock)
    def test_startupjobs_graceful_error_handling(self, mock_sleep, mock_cb, mock_core):
        # Mock engine and context
        mock_engine = MagicMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_engine.get_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Simulate an error during page.evaluate (button click)
        mock_page.evaluate.side_effect = Exception("Simulated browser crash")
        
        # Mock selectors and cards to ensure some data is processed before/after crash
        mock_card = AsyncMock()
        mock_card.get_attribute.return_value = "/job/123"
        mock_page.query_selector_all.return_value = [mock_card]
        
        scraper = StartupJobsScraper(mock_engine, "StartupJobs")
        scraper.config = {'base_url': 'https://test.com', 'card': '.card'}
        
        # Run scraper - it should not raise the exception
        try:
            asyncio.run(scraper.run(limit=10))
            success = True
        except Exception:
            success = False
            
        self.assertTrue(success, "Scraper raised exception instead of handling it gracefully")

if __name__ == '__main__':
    unittest.main()
