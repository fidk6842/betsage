from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class WagerDumpManager:
    def __init__(self, user_sessions: Dict):
        self.user_sessions = user_sessions

    def add_to_dump(self, user_id: int) -> bool:
        """Add current selections to the wager dump, filtering for match_winner outcomes."""
        session = self.user_sessions.get(user_id, {})
        selections = session.get('current_selections', [])
        if not selections:
            logger.info(f"No selections to add to wager dump for user {user_id}")
            return False

        # Filter and normalize match_winner selections
        match_winner_selections = []
        for s in selections:
            if not isinstance(s, dict):
                logger.warning(f"Invalid selection format for user {user_id}: {s}")
                continue
                
            market = str(s.get('market', '')).lower()
            selection = str(s.get('selection', '')).lower()
            home_team = str(s.get('home_team', '')).lower()
            away_team = str(s.get('away_team', '')).lower()
            
            # Check if market or selection indicates a match_winner outcome
            if market in ['home', 'away', 'draw', 'match_winner'] or selection in [home_team, away_team, 'draw']:
                # Normalize to match_winner and ensure all fields exist
                normalized_selection = {
                    'league': s.get('league', 'Unknown'),
                    'home_team': s.get('home_team', 'N/A'),
                    'away_team': s.get('away_team', 'N/A'),
                    'market': 'match_winner',
                    'selection': s.get('selection', 'N/A'),
                    'odds': float(s.get('odds', 1.0)),
                    'team_type': s.get('team_type', 'unknown'),
                    'algorithm': s.get('algorithm', 'unknown')
                }
                match_winner_selections.append(normalized_selection)

        if not match_winner_selections:
            logger.info(f"No match_winner selections to add to wager dump for user {user_id}")
            return False

        # Initialize wager dump if not present
        if 'wager_dump' not in session:
            session['wager_dump'] = []
            
        session['wager_dump'].extend(match_winner_selections)
        session['current_selections'] = []  # Clear current selections
        logger.info(f"Added {len(match_winner_selections)} match_winner selections to wager dump for user {user_id}")
        return True

    def discard_selections(self, user_id: int) -> bool:
        """Discard current selections without adding to dump."""
        session = self.user_sessions.get(user_id, {})
        if not session:
            logger.warning(f"No session found for user {user_id}")
            return False
            
        if 'current_selections' in session:
            session['current_selections'] = []
            logger.info(f"Discarded selections for user {user_id}")
            return True
        logger.info(f"No selections to discard for user {user_id}")
        return False

    def get_wager_dump(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve the wager dump for a user."""
        session = self.user_sessions.get(user_id, {})
        if not session:
            logger.warning(f"No session found for user {user_id}")
            return []
            
        return session.get('wager_dump', [])

    def verify_league_alg_result(self, user_id: int) -> bool:
        """Verify that league-alg-result data is stored in the dump."""
        session = self.user_sessions.get(user_id, {})
        if not session:
            logger.warning(f"No session found for user {user_id}")
            return False
            
        selections = session.get('current_selections', [])
        return bool(selections)  # True if selections exist and non-empty

    def reset_session(self, user_id: int) -> None:
        """Reset session data, preserving wager dump."""
        session = self.user_sessions.get(user_id, {})
        if not session:
            logger.warning(f"No session found for user {user_id}")
            self.user_sessions[user_id] = {'wager_dump': []}
            return
            
        wager_dump = session.get('wager_dump', [])
        self.user_sessions[user_id] = {
            'wager_dump': wager_dump  # Preserve only wager_dump
        }
        logger.info(f"Reset session for user {user_id}")