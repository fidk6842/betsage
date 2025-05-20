# app/features/pdf_strategy/data/pdf_strategy_engine.py
import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from utils.cache import SimpleCache
from config.settings import SCRAPING_API_KEY, SCRAPING_BASE_URL
from app.features.pdf_strategy.rules.odds_decoder import PDFOddsDecoder

logger = logging.getLogger(__name__)

LEAGUE_PREFERENCE = {
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

class PdfStrategyEngine:
    def __init__(self, api_timeout: int = 25):
        logger.info("Initializing PdfStrategyEngine")
        self.api_base = SCRAPING_BASE_URL.rstrip('/')
        self.api_key = SCRAPING_API_KEY
        self.cache = SimpleCache(ttl=330)  # 5.5 minutes
        self.timeout = api_timeout
        self.target_bookmaker = "bet365"
        self.odds_decoder = PDFOddsDecoder()
        self.current_date = datetime.utcnow().date()
        self.min_confidence = 0.75
        self.max_parlay_combinations = 5
        self.league_preference = LEAGUE_PREFERENCE
        logger.debug(f"Engine initialized: date={self.current_date}, timeout={self.timeout}")

    def execute_full_workflow(self, selected_markets: Set[str]) -> List[Dict]:
        """Execute workflow with user-selected markets for today."""
        logger.info(f"Starting full workflow with markets: {selected_markets}")
        try:
            today_matches = self._fetch_today_matches(selected_markets)
            if not today_matches:
                logger.warning("No matches available for today")
                return []
            processed_matches = self._process_and_analyze_matches(today_matches)
            logger.info("Workflow completed successfully")
            return processed_matches
        except Exception as e:
            logger.critical(f"Workflow failure: {str(e)}", exc_info=True)
            return []

    def _fetch_today_matches(self, selected_markets: Set[str]) -> List[Dict]:
        """Fetch matches for today using API-Football and The Odds API."""
        today = self.current_date.strftime("%Y-%m-%d")
        logger.info(f"Fetching matches for today: {today}")
        from app.features.pdf_strategy.data.competition_fetcher import integrate_into_strategy_engine
        all_matches = integrate_into_strategy_engine(selected_markets, today)
        if not all_matches:
            logger.warning("No matches retrieved for today")
            return []
        logger.info(f"Total matches found for today: {len(all_matches)}")
        return all_matches

    def _process_and_analyze_matches(self, raw_matches: List[Dict]) -> List[Dict]:
        """Process fetched matches into recommendations."""
        logger.info(f"Processing {len(raw_matches)} raw matches")
        processed = []
        for match in raw_matches:
            try:
                logger.debug(f"Processing match: {match.get('id', 'unknown')}")
                if not self._validate_match_structure(match):
                    logger.warning(f"Invalid match structure: {match.get('id', 'unknown')}")
                    continue
                odds_data = self._extract_bookmaker_odds(match)
                if not odds_data:
                    logger.warning(f"No odds data for match: {match.get('id', 'unknown')}")
                    continue
                match_analysis = self._analyze_match(match, odds_data)
                formatted_result = self._format_match_result(match, odds_data, match_analysis)
                processed.append(formatted_result)
                logger.debug(f"Processed match: {match['id']}")
            except Exception as e:
                logger.warning(f"Error processing match {match.get('id', 'unknown')}: {str(e)}")
        logger.info(f"Processed {len(processed)} matches successfully")
        return self._generate_strategy_recommendations(processed)

    def _validate_match_structure(self, match: Dict) -> bool:
        """Validate match structure."""
        required_keys = {'id', 'commence_time', 'home_team', 'away_team', 'bookmakers'}
        result = all(key in match for key in required_keys)
        logger.debug(f"Validating match {match.get('id', 'unknown')}: {result}")
        return result

    def _extract_bookmaker_odds(self, match: Dict) -> Optional[Dict]:
        """Extract odds, prioritizing target_bookmaker with fallback."""
        match_id = match.get('id', 'unknown')
        logger.debug(f"Extracting odds for match: {match_id}")
        try:
            bookmakers = match.get('bookmakers', [])
            if not bookmakers:
                logger.warning(f"No bookmakers available for match: {match_id}")
                return None

            bookmaker = next(
                (b for b in bookmakers if b['key'].lower() == self.target_bookmaker.lower()),
                bookmakers[0]  # Fallback to first available
            )
            logger.debug(f"Using bookmaker: {bookmaker['key']} for match: {match_id}")

            market_data = {m['key']: {o['name'].lower(): o['price'] for o in m['outcomes']} for m in bookmaker['markets']}
            home_team_lower = match['home_team'].lower()
            away_team_lower = match['away_team'].lower()
            odds = {
                'home': market_data.get('h2h', {}).get(home_team_lower, market_data.get('h2h', {}).get('home', 0.0)),
                'away': market_data.get('h2h', {}).get(away_team_lower, market_data.get('h2h', {}).get('away', 0.0)),
                'draw': market_data.get('h2h', {}).get('draw', 0.0),
                'over_2.5': market_data.get('totals', {}).get('over', 0.0),
                'under_2.5': market_data.get('totals', {}).get('under', 0.0),
                'btts_yes': market_data.get('btts', {}).get('yes', 0.0),
                'btts_no': market_data.get('btts', {}).get('no', 0.0)
            }
            logger.debug(f"Extracted odds for {match_id}: {odds}")
            return odds
        except Exception as e:
            logger.error(f"Error extracting odds for match {match_id}: {str(e)}")
            return None

    def _analyze_match(self, match: Dict, odds: Dict, selected_markets: Set[str]) -> Dict:
        """Analyze match odds using odds_decoder for selected markets."""
        match_id = match.get('id', 'unknown')
        logger.debug(f"Analyzing match {match_id} with odds: {odds} for markets: {selected_markets}")
        try:
            commence_date = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
            season_period = self._determine_season_period(commence_date)
            analysis = self.odds_decoder.analyze(
                odds=odds,
                season_period=season_period,
                selected_markets=selected_markets
            )
            logger.debug(f"Analysis for {match_id}: {analysis}")
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing match {match_id}: {str(e)}")
            return {'confidence': 0.0}

    def _determine_season_period(self, match_date: datetime) -> str:
        """Determine season period based on match date."""
        month = match_date.month
        if 8 <= month <= 10:
            period = 'early'
        elif 11 <= month <= 2:
            period = 'mid'
        else:
            period = 'late'
        logger.debug(f"Season period for {match_date}: {period}")
        return period

    def _format_match_result(self, match: Dict, odds: Dict, analysis: Dict) -> Dict:
        """Format match result for recommendations."""
        match_id = match['id']
        logger.debug(f"Formatting result for match: {match_id}")
        result = {
            'match_id': match_id,
            'teams': f"{match['home_team']} vs {match['away_team']}",
            'league': match.get('sport_title', 'Unknown League'),
            'commence_time': match['commence_time'],
            'odds': odds,
            'analysis': analysis,
            'profit_score': self._calculate_profit_score(analysis, odds)
        }
        logger.debug(f"Formatted result: {result}")
        return result

    def _calculate_profit_score(self, analysis: Dict, odds: Dict) -> float:
        """Calculate profit score for a match."""
        confidence = analysis.get('confidence', 0.0)
        odds_value = (odds['home'] + odds['away'] + odds.get('over_2.5', 0.0)) / 3
        score = (confidence * 0.65) + (odds_value * 0.35)
        logger.debug(f"Profit score calculated: {score} (confidence={confidence}, odds_value={odds_value})")
        return score

    def _generate_strategy_recommendations(self, matches: List[Dict]) -> List[Dict]:
        """Generate strategy recommendations from processed matches."""
        logger.info(f"Generating recommendations from {len(matches)} matches")
        valid_matches = [m for m in matches if m['analysis']['confidence'] >= self.min_confidence]
        logger.debug(f"Filtered to {len(valid_matches)} matches with confidence >= {self.min_confidence}")
        sorted_matches = sorted(valid_matches, key=lambda x: x['profit_score'], reverse=True)
        logger.info(f"Generated {len(sorted_matches)} strategy recommendations")
        return sorted_matches