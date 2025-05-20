# app/features/pdf_strategy/data/competition_fetcher.py
import requests
from datetime import datetime
import logging
from typing import Set, List, Dict
from config.settings import API_FOOTBALL_KEY, ODDS_API_KEY, SCRAPING_BASE_URL

# Setup logging consistent with OddsBot
logger = logging.getLogger(__name__)

# API URLs
API_FOOTBALL_URL = "https://v3.football.api-sports.io/fixtures"
ODDS_API_BASE_URL = SCRAPING_BASE_URL

LEAGUE_MAPPING = {
    # International Competitions
    "FIFA World Cup": "soccer_fifa_world_cup",
    "UEFA European Championship (EURO)": "soccer_uefa_euro",
    "Copa América": "soccer_conmebol_copa_america",
    "CONCACAF Gold Cup": "soccer_concacaf_gold_cup",
    "Africa Cup of Nations (AFCON)": "soccer_africa_cup_of_nations",
    "AFC Asian Cup": "soccer_afc_asian_cup",
    "OFC Nations Cup": "soccer_ofc_nations_cup",
    "UEFA Nations League": "soccer_uefa_nations_league",

    # Continental Club Competitions
    "UEFA Champions League": "soccer_uefa_champions_league",
    "UEFA Europa League": "soccer_uefa_europa_league",
    "UEFA Conference League": "soccer_uefa_conference_league",
    "Copa Libertadores": "soccer_conmebol_libertadores",
    "Copa Sudamericana": "soccer_conmebol_sudamericana",
    "CONCACAF Champions Cup": "soccer_concacaf_champions_cup",
    "AFC Champions League": "soccer_afc_champions_league",
    "CAF Champions League": "soccer_caf_champions_league",
    "AFC Cup": "soccer_afc_cup",
    "CAF Confederation Cup": "soccer_caf_confederation_cup",
    "FIFA Club World Cup": "soccer_fifa_club_world_cup",

    # Top European Domestic Leagues
    "English Premier League (EPL)": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Bundesliga": "soccer_germany_bundesliga",
    "Serie A": "soccer_italy_serie_a",
    "Ligue 1": "soccer_france_ligue_one",
    "Eredivisie": "soccer_netherlands_eredivisie",
    "Primeira Liga": "soccer_portugal_primeira_liga",
    "Belgian Pro League (Jupiler Pro League)": "soccer_belgium_first_division_a",
    "Russian Premier League": "soccer_russia_premier_league",
    "Swiss Super League": "soccer_switzerland_super_league",
    "Turkish Süper Lig": "soccer_turkey_super_lig",
    "Scottish Premiership": "soccer_scotland_premiership",
    "Austrian Bundesliga": "soccer_austria_bundesliga",
    "Greek Super League": "soccer_greece_super_league",
    "Ukrainian Premier League": "soccer_ukraine_premier_league",
    "Czech First League (Fortuna Liga)": "soccer_czech_republic_first_league",
    "Danish Superliga": "soccer_denmark_superliga",
    "Polish Ekstraklasa": "soccer_poland_ekstraklasa",
    "Norwegian Eliteserien": "soccer_norway_eliteserien",
    "Swedish Allsvenskan": "soccer_sweden_allsvenskan",
    "Romanian Liga I": "soccer_romania_liga_i",
    "Hungarian Nemzeti Bajnokság I (NB I)": "soccer_hungary_nb_i",
    "Serbian SuperLiga": "soccer_serbia_super_liga",
    "Croatian HNL (SuperSport HNL)": "soccer_croatia_first_football_league",

    # Top Non-European Domestic Leagues
    "Major League Soccer (MLS)": "soccer_usa_mls",
    "Brasileirão Serie A": "soccer_brazil_campeonato",
    "Argentine Primera División (Liga Profesional)": "soccer_argentina_primera_division",
    "Mexican Liga MX": "soccer_mexico_liga_mx",
    "Chinese Super League (CSL)": "soccer_china_super_league",
    "Japanese J1 League": "soccer_japan_j_league",
    "Saudi Pro League": "soccer_saudi_arabia_pro_league",

    # Additional Competitions
    "English Championship": "soccer_england_championship",
    "Italian Serie B": "soccer_italy_serie_b",
    "Spanish Segunda División": "soccer_spain_segunda_division",
    "German 2. Bundesliga": "soccer_germany_bundesliga_2",
    "French Ligue 2": "soccer_france_ligue_two",
    "Brazilian Serie B": "soccer_brazil_serie_b",
    "Argentine Primera Nacional": "soccer_argentina_primera_nacional",
    "Mexican Ascenso MX": "soccer_mexico_ascenso_mx",
    "Japanese J2 League": "soccer_japan_j2_league",
    "South African Premier Division": "soccer_south_africa_premier_league"
}

def get_todays_competitions(target_date: str = None) -> Set[str]:
    """Fetch today's competitions from API-Football."""
    date_to_fetch = target_date or datetime.utcnow().strftime("%Y-%m-%d")
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params = {"date": date_to_fetch, "status": "NS"}  # NS = Not Started

    try:
        logger.info(f"Fetching competitions for {date_to_fetch} from API-Football")
        response = requests.get(API_FOOTBALL_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "response" not in data:
            logger.error(f"Unexpected API response format: {data}")
            return set()

        competitions = {fixture["league"]["name"] for fixture in data["response"]}
        logger.info(f"Found {len(competitions)} competitions for {date_to_fetch}")
        logger.debug(f"Competitions: {competitions}")
        return competitions

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching API-Football data: {str(e)}")
        return set()

def match_leagues_to_odds_api(competitions: Set[str]) -> List[str]:
    """Match API-Football competitions to The Odds API sport_keys using exact matching."""
    matched_leagues = []
    for comp in competitions:
        if comp in LEAGUE_MAPPING:
            matched_leagues.append(LEAGUE_MAPPING[comp])
            logger.debug(f"Matched '{comp}' to '{LEAGUE_MAPPING[comp]}'")
    logger.info(f"Matched {len(matched_leagues)} leagues: {matched_leagues}")
    return matched_leagues

def fetch_odds_for_leagues(sport_keys: List[str], selected_markets: Set[str]) -> List[Dict]:
    """Fetch odds from The Odds API for matched leagues and selected markets."""
    all_matches = []
    for sport_key in sport_keys:
        for market in selected_markets:
            try:
                logger.info(f"Fetching {market} odds for {sport_key}")
                response = requests.get(
                    f"{ODDS_API_BASE_URL}/sports/{sport_key}/odds",
                    params={
                        "apiKey": ODDS_API_KEY,
                        "regions": "eu,uk,us,au",  # Broader regions for more odds
                        "markets": market,
                        "oddsFormat": "decimal",
                        "dateFormat": "iso"
                    },
                    timeout=10
                )
                response.raise_for_status()
                matches = response.json()
                today_matches = [m for m in matches if is_today_match(m.get("commence_time"))]
                if today_matches and sport_key == "soccer_usa_mls":
                    logger.debug(f"Sample MLS match: {today_matches[0]}")
                all_matches.extend(today_matches)
                logger.info(f"Fetched {len(today_matches)} {market} matches for {sport_key}")
            except requests.exceptions.HTTPError as e:
                logger.debug(f"HTTP error for {sport_key}, market {market}: {str(e)} - {response.text}")
            except Exception as e:
                logger.error(f"Error fetching odds for {sport_key}, market {market}: {str(e)}")
    logger.info(f"Total matches fetched: {len(all_matches)}")
    return all_matches

def is_today_match(commence_time: str) -> bool:
    """Check if a match is scheduled for today."""
    if not commence_time:
        logger.debug("Commence time missing, returning False")
        return False
    try:
        match_date = datetime.fromisoformat(commence_time.replace("Z", "+00:00")).date()
        return match_date == datetime.utcnow().date()
    except Exception as e:
        logger.error(f"Error parsing commence_time {commence_time}: {str(e)}")
        return False

def integrate_into_strategy_engine(selected_markets: Set[str], target_date: str = None) -> List[Dict]:
    """Integrate API-Football league discovery with Odds API odds fetching."""
    competitions = get_todays_competitions(target_date)
    if not competitions:
        logger.warning("No competitions found for the target date")
        return []
    matched_sport_keys = match_leagues_to_odds_api(competitions)
    if not matched_sport_keys:
        logger.warning("No leagues matched to Odds API keys")
        return []
    matches = fetch_odds_for_leagues(matched_sport_keys, selected_markets)
    return matches

if __name__ == "__main__":
    markets = {"h2h"}
    matches = integrate_into_strategy_engine(markets, "2025-03-22")
    for match in matches[:5]:
        logger.info(f"{match['home_team']} vs {match['away_team']} ({match['sport_key']})")