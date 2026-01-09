
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from scraper import PagedScraper, ScrapeEngine

class TestCocumaPagination:
    @pytest.mark.asyncio
    @patch('scraper.CORE')
    @patch('scraper.CIRCUIT_BREAKER')
    async def test_paged_scraper_stops_on_no_cards(self, mock_cb, mock_core):
        mock_cb.is_open.return_value = False
        mock_engine = MagicMock(spec=ScrapeEngine)
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_engine.get_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Simulate Page 1 has cards, Page 2 has none
        mock_page.query_selector_all.side_effect = [
            [AsyncMock()], # Page 1 cards
            []             # Page 2 cards (empty)
        ]
        
        scraper = PagedScraper(mock_engine, "Cocuma")
        scraper.config = {
            'base_url': 'https://test.com/page/',
            'card': '.card',
            'title': 'h2'
        }
        
        # Run scraper with limit 5, but it should stop after Page 2
        await scraper.run(limit=5)
        
        # Verify it navigated only twice
        assert mock_page.goto.call_count == 2
