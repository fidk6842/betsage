"""Parlay Builder for PDF Strategy Results"""
import math
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class ParlayBuilder:
    def __init__(self, matches: List[Dict]):
        self.matches = matches
        self.min_legs = 2
        self.max_legs = 5
        self.target_odds_range = (5.0, 10.0)
        self.min_confidence = 0.7

    def generate_parlay(self) -> Dict:
        """Generate a parlay with 5-10 odds"""
        qualified = self._filter_qualified_matches()
        if not qualified:
            return {'legs': [], 'total_odds': 0.0, 'confidence': 0.0}
        selected = self._select_diverse_matches(qualified)
        return self._build_parlay(selected)

    def _filter_qualified_matches(self) -> List[Dict]:
        """Filter matches by confidence and valid odds"""
        return [
            m for m in self.matches
            if m['analysis']['confidence'] >= self.min_confidence
            and m['odds']['home'] > 1.0
        ]

    def _select_diverse_matches(self, matches: List[Dict]) -> List[Dict]:
        """Select diverse matches targeting 5-10 odds"""
        leagues = set()
        selected = []
        total_odds = 1.0
        for match in sorted(matches, key=lambda x: x['profit_score'], reverse=True):
            if len(selected) >= self.max_legs or total_odds > self.target_odds_range[1]:
                break
            if match['league'] not in leagues:
                odds = match['odds']['home']
                if total_odds * odds <= self.target_odds_range[1]:
                    selected.append(match)
                    leagues.add(match['league'])
                    total_odds *= odds
            if total_odds >= self.target_odds_range[0] and len(selected) >= self.min_legs:
                break
        return selected if total_odds >= self.target_odds_range[0] else matches[:self.max_legs]

    def _build_parlay(self, selections: List[Dict]) -> Dict:
        """Calculate parlay metrics"""
        if not selections:
            return {'legs': [], 'total_odds': 0.0, 'confidence': 0.0}
        try:
            return {
                'legs': selections,
                'total_odds': round(math.prod(m['odds']['home'] for m in selections), 2),
                'confidence': sum(m['analysis']['confidence'] for m in selections) / len(selections)
            }
        except Exception as e:
            logger.error(f"Parlay calculation error: {str(e)}")
            return {'legs': [], 'total_odds': 0.0, 'confidence': 0.0}