
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from scraper import WttjScraper, ScrapeEngine

class TestWttjRateLimit:
    @pytest.mark.asyncio
    @patch('scraper.rate_limit')
    @patch('scraper.CORE')
    @patch('scraper.CIRCUIT_BREAKER')
    async def test_wttj_uses_custom_rate_limit(self, mock_cb, mock_core, mock_rate_limit):
        mock_cb.is_open.return_value = False
        mock_engine = MagicMock(spec=ScrapeEngine)
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_engine.get_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock cards to allow one page execution
        mock_page.query_selector_all.return_value = []
        
        scraper = WttjScraper(mock_engine, "WTTJ")
        scraper.config = {'base_url': 'https://test.com', 'card': '.card', 'link': 'a'}
        
        await scraper.run(limit=1)
        
        # Verify rate_limit was called with custom WTTJ bounds
        # (3.0, 7.0)
        mock_rate_limit.assert_called_with(3.0, 7.0)
