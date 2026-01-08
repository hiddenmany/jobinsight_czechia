
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from scraper import StartupJobsScraper

class TestIncrementalPersistence(unittest.TestCase):
    @patch('scraper.CORE')
    @patch('scraper.CIRCUIT_BREAKER')
    @patch('scraper.asyncio.sleep', new_callable=AsyncMock)
    async def test_startupjobs_incremental_persistence(self, mock_sleep, mock_cb, mock_core):
        # Mocking requirements
        mock_cb.is_open.return_value = False
        
        # Mock engine and context
        mock_engine = MagicMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_engine.get_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock selectors and cards
        mock_card = AsyncMock()
        mock_card.get_attribute.return_value = "/job/123"
        mock_card.inner_text.return_value = "Title\nCompany\n50000 Kč"
        
        mock_page.query_selector_all.return_value = [mock_card] * 10
        mock_page.evaluate.side_effect = [True, False] # Click once then stop
        
        scraper = StartupJobsScraper(mock_engine, "StartupJobs")
        scraper.config = {
            'base_url': 'https://test.com',
            'card': '.card',
            'domain': 'https://test.com'
        }
        
        # We want to verify that add_signal is called during the loop, 
        # not just at the very end.
        # This is tricky without actually running the loop.
        # I'll implement the feature first then verify.
        pass

if __name__ == '__main__':
    unittest.main()
