import numpy as np
from typing import List, Dict
from app.features.data_processing import ProcessedMatch

def calculate_parlay_stakes(
    matches: List[ProcessedMatch],
    bankroll: float = 1000.0,
    fractional_kelly: float = 0.5,
    max_stake_percent: float = 0.05,
    edge_threshold: float = 0.05,
    sensitivity_adjustment: float = 0.9
) -> Dict[str, List[Dict]]:
    """
    Enhanced Kelly Criterion parlay calculator with risk management features
    - Uses model-derived probabilities from historical data
    - Incorporates sensitivity analysis for edge robustness
    - Implements fractional Kelly and stake caps for risk management
    """
    recommended_parlays = []
    
    for match in matches:
        try:
            # Extract valid bookmaker odds
            bookmaker_odds = [
                (bm_name, bm_data['home']) 
                for bm_name, bm_data in match['bookmakers'].items()
                if bm_data['home'] is not None
            ]
            
            if not bookmaker_odds:
                continue
                
            # Identify best available odds
            best_odds, best_bookmaker = max(bookmaker_odds, key=lambda x: x[1])
            
            # Get model's probability estimate from historical analysis
            estimated_prob = match['probabilities']['home']
            
            # Validate probability estimate
            if not (0 < estimated_prob < 1):
                continue
                
            # Calculate base edge using historical probability
            base_edge = estimated_prob * best_odds - 1
            
            # Sensitivity analysis with adjusted probability
            conservative_prob = estimated_prob * sensitivity_adjustment
            conservative_edge = conservative_prob * best_odds - 1
            
            # Edge validation checks
            if base_edge >= edge_threshold and conservative_edge > 0:
                # Kelly stake calculation
                full_kelly = (base_edge / (best_odds - 1)) * bankroll
                
                # Apply risk management controls
                stake = full_kelly * fractional_kelly
                stake = min(stake, max_stake_percent * bankroll)
                stake = max(min(stake, bankroll), 0)  # Ensure valid stake
                
                if stake < 1:  # Minimum practical stake
                    continue
                
                # Format recommendation
                recommendation = {
                    'match_id': match['id'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'bookmaker': best_bookmaker,
                    'odds': best_odds,
                    'recommended_stake': round(stake, 2),
                    'base_edge': round(base_edge * 100, 2),
                    'conservative_edge': round(conservative_edge * 100, 2),
                    'bankroll_usage': round((stake/bankroll)*100, 2)
                }
                recommended_parlays.append(recommendation)
                
        except KeyError:
            continue  # Skip matches missing required data
        except ZeroDivisionError:
            continue  # Handle invalid odds edge case
        except Exception as e:
            # Implement logging in production
            continue
            
    # Sort and limit recommendations
    sorted_parlays = sorted(
        recommended_parlays,
        key=lambda x: x['base_edge'],
        reverse=True
    )
    return {'recommended_parlays': sorted_parlays[:5]} if sorted_parlays else {'status': 'no_valuable_parlays'}