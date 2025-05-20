from typing import Dict, List, Set, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# League data: key -> (display_name, api_key)
LEAGUE_DATA = {
    'epl': ('🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', 'soccer_epl'),
    'la_liga': ('🇪🇸 La Liga', 'soccer_spain_la_liga'),
    'bundesliga': ('🇩🇪 Bundesliga', 'soccer_germany_bundesliga'),
    'serie_a': ('🇮🇹 Serie A', 'soccer_italy_serie_a'),
    'ligue_1': ('🇫🇷 Ligue 1', 'soccer_france_ligue_one'),
    'champions': ('🏆 UCL', 'soccer_uefa_champions_league')
}

# Algorithm data: key -> (display_name, description)
ALGORITHM_DATA = {
    'arima': ('📈 ARIMA', 'Time Series Analysis'),
    'kelly': ('💰 Kelly', 'Stake Optimization'),
    'monte': ('🎲 Monte Carlo', 'Simulations'),
    'ipt': ('⚖️ IPT', 'Implied Probability'),
    'arb': ('🔀 Arbitrage', 'Opportunity Detection'),
    'value': ('📊 Value Bets', 'Odds Comparison')
}

# Market data: key -> (display_name, api_key)
MARKET_DATA = {
    "match_winner": ("Match Winner", "match_winner"),
    "both_teams_to_score": ("Both Teams To Score", "both_teams_to_score"),
    "over_under": ("Over Under", "over_under"),
    "correct_score": ("Correct Score", "correct_score")
}

def load_market_data() -> None:
    """Load market data from config if available, else use fallback."""
    global MARKET_DATA
    try:
        from config.market_config import AVAILABLE_MARKETS
        # Flatten AVAILABLE_MARKETS for button display
        market_data_update = {
            market: (market.replace('_', ' ').title(), market)
            for group in AVAILABLE_MARKETS.values()
            for market in group
        }
        MARKET_DATA.update(market_data_update)
    except ImportError:
        pass  # Use hardcoded MARKET_DATA as fallback

def create_grid(items: Dict, prefix: str, cols: int = 2) -> List[List[InlineKeyboardButton]]:
    """
    Create a grid of buttons from dictionary items.
    
    Args:
        items: Dictionary of items where key is the callback data suffix and value is (display_text, optional_data)
        prefix: Prefix for callback data
        cols: Number of columns in the grid
        
    Returns:
        List of rows, where each row is a list of InlineKeyboardButton objects
    """
    # Convert items to list for slicing
    items_list = list(items.items())
    
    # Create rows with 'cols' buttons per row
    rows = [items_list[i:i+cols] for i in range(0, len(items_list), cols)]
    
    # Create buttons for each row
    buttons = []
    for row in rows:
        button_row = []
        for key, (display_text, _) in row:
            button_row.append(
                InlineKeyboardButton(display_text, callback_data=f"{prefix}:{key}")
            )
        buttons.append(button_row)
        
    return buttons

def main_menu_markup(show_build_parlay: bool = False) -> InlineKeyboardMarkup:
    """
    Generate the main menu keyboard with conditional 'Build Parlay' button.
    """
    buttons = [
        [InlineKeyboardButton("🤖 BetSage AI", callback_data="menu:leagues")],
        [InlineKeyboardButton("📚 PDF Strategy", callback_data="pdf:strategy")],
        [InlineKeyboardButton("❓ Help Center", callback_data="help:guide")],
    ]
    
    if show_build_parlay:
        buttons.append([InlineKeyboardButton("🎯 Build Parlay", callback_data="action:build_parlay")])
        
    buttons.append([InlineKeyboardButton("🔄 Refresh Data", callback_data="action:refresh")])
    
    return InlineKeyboardMarkup(buttons)

def league_selector_markup() -> InlineKeyboardMarkup:
    """
    Generate the league selection keyboard.
    
    Returns:
        InlineKeyboardMarkup for league selection
    """
    buttons = create_grid(LEAGUE_DATA, 'league')
    buttons.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu:main")])
    
    return InlineKeyboardMarkup(buttons)

def algorithm_selector_markup(paid_user: bool = False) -> InlineKeyboardMarkup:
    """
    Generate the algorithm selection keyboard.
    
    Args:
        paid_user: Whether the user has paid for premium features
        
    Returns:
        InlineKeyboardMarkup for algorithm selection
    """
    if not paid_user:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Demo Analysis", callback_data="algo:demo")],
            [InlineKeyboardButton("💎 Upgrade", callback_data="payment:upgrade")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu:leagues")]
        ])
        
    buttons = create_grid(ALGORITHM_DATA, 'algo')
    buttons.append([
        InlineKeyboardButton("🔙 Back", callback_data="menu:leagues"),
        InlineKeyboardButton("🏠 Home", callback_data="menu:main")
    ])
    
    return InlineKeyboardMarkup(buttons)

def market_selector_markup(selected: Optional[Set[str]] = None) -> InlineKeyboardMarkup:
    """
    Generate the market selection keyboard.
    
    Args:
        selected: Set of currently selected market keys
        
    Returns:
        InlineKeyboardMarkup for market selection
    """
    load_market_data()  # Ensure market data is loaded
    
    selected = selected or set()
    
    # Create market buttons with selection indicators
    buttons = []
    market_items = list(MARKET_DATA.items())
    
    # Create rows with 2 buttons per row
    for i in range(0, len(market_items), 2):
        row = []
        for j in range(2):
            if i + j < len(market_items):
                key, (display_text, _) = market_items[i + j]
                # Add a check mark to selected markets
                prefix = "✅ " if key in selected else ""
                row.append(
                    InlineKeyboardButton(f"{prefix}{display_text}", callback_data=f"market:{key}")
                )
        buttons.append(row)
    
    # Add control buttons
    buttons.append([
        InlineKeyboardButton("✅ Done", callback_data="market:done"),
        InlineKeyboardButton("🔙 Back", callback_data="pdf:analyze")
    ])
    
    return InlineKeyboardMarkup(buttons)

def help_navigation_markup() -> InlineKeyboardMarkup:
    """
    Generate the help navigation keyboard.
    
    Returns:
        InlineKeyboardMarkup for help navigation
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Wager Guide", callback_data='tool:wager_guide'),
         InlineKeyboardButton("📖 Algorithm Docs", callback_data='tool:algo_docs')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='menu:main')]
    ])

def admin_menu_markup() -> InlineKeyboardMarkup:
    """
    Generate the admin menu keyboard.
    
    Returns:
        InlineKeyboardMarkup for admin menu
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 User Management", callback_data="admin:users")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin:stats")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu:main")]
    ])

def user_management_markup() -> InlineKeyboardMarkup:
    """
    Generate the user management keyboard.
    
    Returns:
        InlineKeyboardMarkup for user management
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Verify User", callback_data="admin:verify")],
        [InlineKeyboardButton("🚫 Block User", callback_data="admin:block")],
        [InlineKeyboardButton("🔓 Unblock User", callback_data="admin:unblock")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin:menu")]
    ])

def result_actions_markup() -> InlineKeyboardMarkup:
    """
    Generate the result actions keyboard.
    
    Returns:
        InlineKeyboardMarkup for result actions
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to BetSlip", callback_data="action:add_to_betslip")],
        [InlineKeyboardButton("🔙 Back to Leagues", callback_data="menu:leagues")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]
    ])

def parlay_actions_markup() -> InlineKeyboardMarkup:
    """
    Generate the parlay actions keyboard.
    
    Returns:
        InlineKeyboardMarkup for parlay actions
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Build Another", callback_data="action:build_parlay")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]
    ])

def wager_dump_actions_markup() -> InlineKeyboardMarkup:
    """
    Generate the wager dump actions keyboard.
    
    Returns:
        InlineKeyboardMarkup for wager dump actions
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add to Dump", callback_data="action:add_to_dump"),
            InlineKeyboardButton("🗑️ Discard", callback_data="action:discard")
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]
    ])


def error_actions_markup(show_build_parlay: bool = False) -> InlineKeyboardMarkup:
    """
    Generate the error actions keyboard.
    
    Args:
        show_build_parlay: Whether to show the Build Parlay button
        
    Returns:
        InlineKeyboardMarkup for error actions
    """
    buttons = [[InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]]
    
    if show_build_parlay:
        buttons.insert(0, [InlineKeyboardButton("🎯 Build Parlay", callback_data="action:build_parlay")])
        
    return InlineKeyboardMarkup(buttons)

def get_markup(markup_type: str, **kwargs) -> InlineKeyboardMarkup:
    """
    Factory function to get the appropriate markup based on type.
    
    Args:
        markup_type: Type of markup to generate
        **kwargs: Additional arguments for specific markup types
        
    Returns:
        InlineKeyboardMarkup object
    """
    markup_methods = {
        'main_menu': main_menu_markup,
        'league_selector': league_selector_markup,
        'algorithm_selector': algorithm_selector_markup,
        'market_selector': market_selector_markup,
        'help_navigation': help_navigation_markup,
        'admin_menu': admin_menu_markup,
        'user_management': user_management_markup,
        'result_actions': result_actions_markup,
        'parlay_actions': parlay_actions_markup,
        'error_actions': error_actions_markup,
        'wager_dump_actions': wager_dump_actions_markup
    }
    
    method = markup_methods.get(markup_type)
    if not method:
        # Default to main menu if type not found
        return main_menu_markup(**kwargs)
        
    return method(**kwargs)