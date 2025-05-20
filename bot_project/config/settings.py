# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(PROJECT_ROOT / ".env")

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
SCRAPING_API_KEY = os.getenv("SCRAPING_API_KEY")
SCRAPING_BASE_URL = os.getenv("SCRAPING_BASE_URL", "https://api.the-odds-api.com/v4")
ODDS_API_KEY = SCRAPING_API_KEY
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/BetSage.db")

# Validate required environment variables
required_vars = {
    "BOT_TOKEN": BOT_TOKEN,
    "SCRAPING_API_KEY": SCRAPING_API_KEY,
    "SCRAPING_BASE_URL": SCRAPING_BASE_URL,
    "API_FOOTBALL_KEY": API_FOOTBALL_KEY,
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")