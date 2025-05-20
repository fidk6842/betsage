"""PDF odds interpretation rules with validation"""
from typing import Dict, Set

class PDFOddsDecoder:
    RULES = {
        (1.10, 1.19): ("under_1.5_ht", 0.95),
        (1.20, 1.29): ("straight_win", 0.90),
        (1.30, 1.44): ("low_scoring_league_win", 0.85),
        (1.50, 1.61): ("risky_win", 0.75),
        (3.00, 3.39): ("ft_draw_xht", 0.80),
        (3.40, 3.60): ("high_scoring_draw", 0.70)
    }

    def analyze_odds(self, odds: float, is_start_of_season: bool) -> Dict:
        """Apply PDF rules with input validation"""
        try:
            rounded = round(float(odds), 2)
            if rounded <= 0:
                raise ValueError("Odds must be positive")
                
            return self._apply_rules(rounded, is_start_of_season)
        except (TypeError, ValueError):
            return self._error_response()
    def analyze(self, odds: Dict[str, float], season_period: str, selected_markets: Set[str]) -> Dict[str, Dict]:
        """Analyze match odds for selected markets"""
        is_start_of_season = (season_period == 'early')
        analyses = {}
        # Analyze head-to-head markets if selected
        if 'h2h' in selected_markets:
            analyses['home'] = self.analyze_odds(odds.get('home', 0.0), is_start_of_season)
            analyses['away'] = self.analyze_odds(odds.get('away', 0.0), is_start_of_season)
            analyses['draw'] = self.analyze_odds(odds.get('draw', 0.0), is_start_of_season)
        # Analyze totals markets if selected
        if 'totals' in selected_markets:
            analyses['over_2.5'] = self.analyze_odds(odds.get('over_2.5', 0.0), is_start_of_season)
            analyses['under_2.5'] = self.analyze_odds(odds.get('under_2.5', 0.0), is_start_of_season)
        return analyses

    def _apply_rules(self, odds: float, season_start: bool) -> Dict:
        """Match odds to known rules"""
        for (low, high), (pred, conf) in self.RULES.items():
            if low <= odds <= high:
                return self._build_response(pred, conf, odds, season_start)
        return self._error_response()

    def _build_response(self, prediction: str, 
                       base_conf: float,
                       odds: float,
                       season_start: bool) -> Dict:
        """Construct analysis response"""
        confidence = base_conf * 1.2 if season_start else base_conf
        return {
            'prediction': prediction,
            'confidence': min(round(confidence, 2), 1.0),
            'original_odds': odds
        }

    def _error_response(self) -> Dict:
        """Default error response"""
        return {
            'prediction': 'no_rule_match',
            'confidence': 0.0,
            'original_odds': 0.0
        }