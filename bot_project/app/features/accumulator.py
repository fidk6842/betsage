import random
import logging
from typing import List, Dict, Any
from functools import reduce
import operator

# Configure logging
typing_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ParlayCombination:
    """
    Represents a single parlay:
      - selections: list of bet dictionaries
      - total_odds: product of all selection odds
    """
    def __init__(self, selections: List[Dict[str, Any]]):
        self.selections = selections
        self.total_odds = reduce(operator.mul, (s['odds'] for s in selections), 1.0)

    def __str__(self):
        return (
            f"Parlay with {len(self.selections)} legs, odds: {self.total_odds:.2f}"
        )

class SmartParlayBuilder:
    def __init__(
        self,
        min_legs: int = 1,
        max_legs: int = 12,
        min_total_odds: float = 10.0,
        max_total_odds: float = 20.0,
        max_individual_odds: float = 4.0,
    ):
        self.min_legs = min_legs
        self.max_legs = max_legs
        self.min_total_odds = min_total_odds
        self.max_total_odds = max_total_odds
        self.max_individual_odds = max_individual_odds

    def _filter_selections(self, selections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Keep only 'match_winner' market bets with reasonable odds,
        and dedupe per match by lowest odds.
        """
        typing_logger.info("Filtering %d raw selections", len(selections))
        filtered = [s for s in selections
                    if s.get('market') == 'match_winner'
                    and 1.01 < s.get('odds', 0) <= self.max_individual_odds]
        unique = {}
        for s in filtered:
            key = (s['home_team'], s['away_team'])
            if key not in unique or s['odds'] < unique[key]['odds']:
                unique[key] = s
        result = list(unique.values())
        typing_logger.info("Filtered down to %d selections", len(result))
        return result

    def _build_parlay(self, selections: List[Dict[str, Any]]) -> ParlayCombination:
        """
        Build a single random parlay:
          1. Choose a random size between min_legs and max_legs (capped to pool size).
          2. Sample that many selections.
          3. Sort by odds and include until max_total_odds is breached.
        """
        size = random.randint(self.min_legs, min(self.max_legs, len(selections)))
        picks = random.sample(selections, size)
        picks.sort(key=lambda x: x['odds'])

        chosen = []
        cum_odds = 1.0
        for pick in picks:
            new_odds = cum_odds * pick['odds']
            if new_odds <= self.max_total_odds:
                chosen.append(pick)
                cum_odds = new_odds
        # Ensure minimum legs and minimum odds
        if len(chosen) < self.min_legs or cum_odds < self.min_total_odds:
            # Retry until a valid parlay is found
            return self._build_parlay(selections)
        return ParlayCombination(chosen)

    def generate_parlay(self, selections: List[Dict[str, Any]]) -> ParlayCombination:
        """
        Public method to filter input and build a new parlay.
        Intended to be called whenever the user clicks the "Generate Parlay" button.
        """
        clean = self._filter_selections(selections)
        if not clean:
            typing_logger.warning("No valid selections after filtering.")
            return ParlayCombination([])
        return self._build_parlay(clean)
 
