"""Robust odds processing with validation and caching"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.sql import text
from utils.cache import SimpleCache
from ..rules.odds_decoder import PDFOddsDecoder

logger = logging.getLogger(__name__)

class OddsProcessor:
    def __init__(self, db_manager):
        self.db = db_manager
        self.cache = SimpleCache(ttl=300)
        self.decoder = PDFOddsDecoder()
        self.required_fields = {'id', 'home_odds', 'match_date', 'is_cup'}

    def process_matches(self, days_ahead: int = 3) -> List[Dict]:
        """Main processing workflow with error containment"""
        try:
            raw_matches = self.db.get_matches_with_odds(days_ahead)
            return [p for m in raw_matches if (p := self._process_match(m))]
        except Exception as e:
            logger.critical(f"Processing failed: {str(e)}", exc_info=True)
            return []

    def _process_match(self, match: Dict) -> Optional[Dict]:
        """Individual match processing pipeline"""
        if not self._validate_match(match):
            return None
            
        cache_key = f"odds:{match['id']}"
        if cached := self.cache.get(cache_key):
            return cached
            
        try:
            processed = self._create_processed_entry(match)
            self.cache.set(cache_key, processed)
            return processed
        except Exception as e:
            logger.warning(f"Skipping match {match.get('id')}: {str(e)}")
            return None

    def _validate_match(self, match: Dict) -> bool:
        """Comprehensive data validation"""
        if not self.required_fields.issubset(match.keys()):
            logger.warning(f"Missing fields in match {match.get('id')}")
            return False
            
        try:
            match['home_odds'] = float(match['home_odds'])
            datetime.fromisoformat(str(match['match_date']))
            return True
        except (TypeError, ValueError):
            logger.warning(f"Invalid data types in match {match.get('id')}")
            return False

    def _create_processed_entry(self, match: Dict) -> Dict:
        """Create processed match entry with analysis"""
        is_season_start = self._is_start_of_season(match['match_date'])
        analysis = self.decoder.analyze_odds(
            odds=match['home_odds'],
            is_start_of_season=is_season_start
        )
        
        return {
            'match_id': match['id'],
            'league': match.get('league', 'UNKNOWN'),
            'prediction': analysis.get('prediction', 'unavailable'),
            'confidence': self._sanitize_confidence(analysis.get('confidence', 0.0)),
            'odds': match['home_odds'],
            'is_cup': match['is_cup'],
            'recommended_bet': f"{analysis['prediction']} @ {match['home_odds']:.2f}"
        }

    def _is_start_of_season(self, match_date: datetime) -> bool:
        """Determine if match is in season start window"""
        try:
            return 8 <= match_date.month <= 10
        except AttributeError:
            return False

    def _sanitize_confidence(self, value: float) -> float:
        """Ensure confidence within valid range"""
        return min(max(round(float(value), 2), 0.0), 1.0)