
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from scraper import ScrapeEngine, JobSignal
from playwright.async_api import Error as PlaywrightError

class TestConnectionResilience:
    @pytest.mark.asyncio
    @patch('scraper.Stealth')
    @patch('scraper.rate_limit')
    async def test_scrape_detail_retries_on_connection_closed(self, mock_rate_limit, mock_stealth):
        # Configure stealth mock
        mock_stealth_inst = MagicMock()
        mock_stealth_inst.apply_stealth_async = AsyncMock()
        mock_stealth.return_value = mock_stealth_inst
        
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Simulate net::ERR_CONNECTION_CLOSED on first call, success on second
        mock_page.goto.side_effect = [
            PlaywrightError("net::ERR_CONNECTION_CLOSED"),
            None # Success
        ]
        
        # Mock evaluation results
        mock_page.evaluate.side_effect = ["Desc", "Benefits"]
        
        engine = ScrapeEngine(mock_browser)
        signal = JobSignal(title="Dev", company="Test", link="https://test.com", source="Test")
        
        await engine.scrape_detail(mock_context, signal)
        
        # Verify it called goto twice (1 fail + 1 retry)
        # Note: ScrapeEngine.scrape_detail is already decorated with @retry
        # We want to ensure it catches THIS specific error
        assert mock_page.goto.call_count == 2
        assert signal.description == "Desc"
