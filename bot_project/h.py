# test_mls_bet365_odds.py
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# API Configuration
ODDS_API_KEY = "5e7c0ecd8ac0dfe9a525018db1f14fef"  # Your key
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_usa_mls"
MARKET = "h2h"
BOOKMAKER = "bet365"

def fetch_mls_bet365_odds():
    """Fetch MLS odds from The Odds API for Bet365 only."""
    url = f"{ODDS_API_BASE_URL}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu,uk",
        "markets": MARKET,
        "oddsFormat": "decimal",
        "bookmakers": BOOKMAKER,
        "dateFormat": "iso"
    }

    try:
        logger.info(f"Fetching odds for {SPORT_KEY} with params: {params}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Log the full response
        logger.info(f"Raw API response: {data}")

        # Filter for today's matches
        today = datetime.utcnow().date()
        today_matches = [
            match for match in data
            if datetime.fromisoformat(match.get("commence_time").replace("Z", "+00:00")).date() == today
        ]

        if not data:
            logger.warning("No data returned from the API.")
            return []

        logger.info(f"Total matches returned: {len(data)}")
        logger.info(f"Matches for today ({today}): {len(today_matches)}")
        
        if today_matches:
            logger.info(f"First match sample: {today_matches[0]}")
        else:
            logger.warning("No matches found for today.")

        return today_matches

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e} - Response: {response.text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return []

if __name__ == "__main__":
    matches = fetch_mls_bet365_odds()
    logger.info(f"Test complete. Retrieved {len(matches)} matches.")