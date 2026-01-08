
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from scraper import BaseScraper, ScrapeEngine

class TestScraperDiagnostics:
    @pytest.fixture
    def scraper(self):
        mock_engine = MagicMock(spec=ScrapeEngine)
        scraper = BaseScraper(mock_engine, "TestSite")
        scraper.config = {
            'company_selectors': ['.company'],
            'city_selectors': ['.city']
        }
        return scraper

    @pytest.mark.asyncio
    @patch('scraper.logger')
    async def test_extract_company_logs_missing_selector(self, mock_logger, scraper):
        # Mock card with no company selector
        mock_card = AsyncMock()
        mock_card.query_selector.return_value = None
        
        company = await scraper.extract_company(mock_card)
        
        assert company == "Unknown Employer"
        # Verify diagnostic logging - this is expected to fail initially
        mock_logger.debug.assert_any_call("TestSite: Company selector '.company' returned no element")

    @pytest.mark.asyncio
    @patch('scraper.logger')
    async def test_extract_city_logs_missing_selector(self, mock_logger, scraper):
        mock_card = AsyncMock()
        mock_card.query_selector.return_value = None
        mock_card.inner_text.return_value = "No city here"
        
        city = await scraper.extract_city(mock_card)
        
        assert city == "CZ"
        # Verify diagnostic logging - this is expected to fail initially
        mock_logger.debug.assert_any_call("TestSite: City selector '.city' returned no element")
