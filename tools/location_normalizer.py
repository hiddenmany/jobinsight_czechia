
import re
import unicodedata

class LocationNormalizer:
    """Normalizes job location strings into canonical regions and cities."""
    
    def __init__(self):
        # Compiled patterns for main regions
        self.patterns = {
            "Prague": re.compile(r"\b(praha|prague)\b", re.IGNORECASE),
            "Brno": re.compile(r"\bbrno\b", re.IGNORECASE),
            "Ostrava": re.compile(r"\bostrava\b", re.IGNORECASE)
        }
    
    def _normalize_basic(self, text: str) -> str:
        """Basic text normalization: NFKD, lowercase, strip."""
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text)
        return text.lower().strip()

    def normalize(self, location_str: str) -> tuple[str, str]:
        """
        Maps a location string to (Region, City).
        
        Examples:
            "Praha 4" -> ("Prague", "Prague")
            "Brno-město" -> ("Brno", "Brno")
            "Ostrava" -> ("Ostrava", "Ostrava")
            "Plzeň" -> ("Other", "Plzeň")
        """
        if not location_str:
            return "Unknown", "Unknown"
            
        clean_loc = self._normalize_basic(location_str)
        
        # Check for main hubs
        for region, pattern in self.patterns.items():
            if pattern.search(clean_loc):
                return region, region # For hubs, city = region name (canonical)
        
        # Fallback for others
        # Return "Other" as region and the cleaned original string as city
        # But let's keep the city name slightly more original (just stripped/normalized)
        city = location_str.split(',')[0].strip() # Get the city part before comma
        return "Other", city
