import logging
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from typing import List, Dict, Any, Optional, Set
from data.user_manager import UserManager
from app.features.odds_fetcher import fetch_odds_for_league
from app.features.data_processing import preprocess_odds, process_pipeline
from app.features.result_formatter import format_results
from app.interactions.league_selection import LeagueManager
from config.settings import BOT_TOKEN, SCRAPING_API_KEY, SCRAPING_BASE_URL
from utils.logger import setup_logging
from app.features.pdf_strategy.data.database import init_db, Session
from app.features.pdf_strategy.data.pdf_strategy_engine import PdfStrategyEngine
from app.features.algorithms.arima import analyze_odds_movement
from app.features.algorithms.dfs import detect_arbitrage
from app.features.algorithms.kelly import calculate_parlay_stakes
from app.features.algorithms.monte_carlo import simulate_outcomes
from app.features.algorithms.ipt import implied_probability_threshold_model
from app.features.algorithms.ocm import odds_comparison_model
from app.features.pdf_strategy.core.odds_processor import OddsProcessor
from app.features.pdf_strategy.core.parlay_builder import ParlayBuilder
from app.features.pdf_strategy.data.db_connector import DatabaseManager 
from app.features.wager_dump import WagerDumpManager
from app.interactions.inline_buttons import get_markup 
from app.features.accumulator import SmartParlayBuilder 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class BetSageAIBot:
    def __init__(self):
        self.db_manager = DatabaseManager(Session)
        self.league_manager = LeagueManager()
        self.user_manager = UserManager()
        self.user_sessions = {}
        self.wager_dump_manager = WagerDumpManager(self.user_sessions)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command or main menu callback"""
        query = update.callback_query
        user_id = update.effective_user.id
        show_build_parlay = self.should_show_build_parlay(user_id)
        
        if query:
            await query.answer()
            await query.edit_message_text(
                "⚽ Welcome to BetSageAI!\nSelect an option below:",
                reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
            )
        else:
            logger.info(f"User {user_id} started the bot")
            if self.user_manager.is_blocked(user_id):
                await update.message.reply_text("❌ Access denied")
                return
                
            text = "Welcome to BetSageAI!" if self.user_manager.is_paid(user_id) else "⚡ DEMO VERSION ⚡\nUse /pay to unlock full version"
            await update.message.reply_text(
                text, 
                reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
            )

    async def show_help(self, query, context, values=None):
        """Display help information"""
        user_id = query.from_user.id
        show_build_parlay = self.should_show_build_parlay(user_id)
        
        help_text = (
            "🤖 **BetSageAI Help**\n\n"
            "• `/start` - Open main menu\n"
            "• Select a league to analyze\n"
            "• Choose an algorithm for predictions\n"
            "• Add selections to your betslip\n"
            "• Build smart parlays with accumulated selections\n\n"
            "For support, contact @YourSupportUsername"
        )
        
        await query.edit_message_text(
            help_text, 
            parse_mode="Markdown",
            reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
        )

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /pay command"""
        user_id = update.effective_user.id
        show_build_parlay = self.should_show_build_parlay(user_id)
        
        payment_text = (
            "🔐 **Upgrade to Full Version**\n\n"
            f"Send 0.1 ETH to:\n`{self.user_manager.get_crypto_address()}`\n\n"
            "After payment, forward the transaction receipt to @YourAdminUsername"
        )
        
        await update.message.reply_text(
            payment_text, 
            parse_mode="Markdown", 
            reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
        )

    async def verify_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to verify a user's payment"""
        user_id = update.effective_user.id
        
        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text("❌ Admin access required")
            return
            
        try:
            target_user = int(context.args[0])
            self.user_manager.add_paid_user(target_user)
            await update.message.reply_text(f"✅ User {target_user} activated")
            
            show_build_parlay = self.should_show_build_parlay(target_user)
            await context.bot.send_message(
                chat_id=target_user,
                text="🎉 Payment verified! Full access granted.",
                reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
            )
        except (IndexError, ValueError) as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def block_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to block a user"""
        user_id = update.effective_user.id
        
        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text("❌ Admin access required")
            return
            
        try:
            target_user = int(context.args[0])
            self.user_manager.block_user(target_user)
            await update.message.reply_text(f"✅ User {target_user} blocked")
        except (IndexError, ValueError) as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries from inline buttons"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data_parts = query.data.split(':')
        action = data_parts[0]
        values = data_parts[1:] if len(data_parts) > 1 else []

        if action == 'admin' and self.user_manager.is_admin(user_id):
            await self._handle_admin_actions(query, context, values)
            return

        handler_map = {
            'menu': self.handle_menu,
            'league': self.handle_league_selection,
            'algo': self.handle_algorithm_selection,
            'pdf': self.handle_pdf_strategy,
            'market': self.handle_market_selection,
            'help': self.show_help,
            'action': self.handle_action
        }

        if action == 'action':
            action_type = values[0] if values else None
            if action_type == 'build_parlay':
                await self.build_parlay(query, context)
            elif action_type == 'refresh':
                await self._handle_refresh(query, context)
            elif action_type == 'add_to_dump':
                await self._handle_add_to_dump(query, context)
            elif action_type == 'discard':
                await self._handle_discard(query, context)
            else:
                await self.show_error(query, "Invalid action")
        elif handler := handler_map.get(action):
            await handler(query, context, values)
        else:
            await self.show_error(query, "Unknown action")
            
    async def _handle_add_to_dump(self, query, context):
        """Handle adding selections to wager dump"""
        user_id = query.from_user.id
        success = self.wager_dump_manager.add_to_dump(user_id)
        message = "✅ Selections added to wager dump!" if success else "❌ No selections to add."
        await query.edit_message_text(
            message,
            reply_markup=get_markup('main_menu', show_build_parlay=self.should_show_build_parlay(user_id))
        )
        self.wager_dump_manager.reset_session(user_id)

    async def _handle_discard(self, query, context):
        """Handle discarding selections"""
        user_id = query.from_user.id
        success = self.wager_dump_manager.discard_selections(user_id)
        message = "✅ Selections discarded." if success else "❌ No selections to discard."
        await query.edit_message_text(
            message,
            reply_markup=get_markup('main_menu', show_build_parlay=self.should_show_build_parlay(user_id))
        )
        self.wager_dump_manager.reset_session(user_id)

    async def _handle_refresh(self, query, context):
        """Handle refreshing data"""
        user_id = query.from_user.id
        show_build_parlay = self.should_show_build_parlay(user_id)
        
        await query.edit_message_text(
            "🔄 Refreshing data...",
            reply_markup=None
        )
        
        # Simulate refresh operation
        # In a real implementation, you would update data from API here
        
        await query.edit_message_text(
            "✅ Data refreshed successfully!",
            reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
        )

    def should_show_build_parlay(self, user_id: int) -> bool:
        """Check if 'Build Parlay' button should be shown."""
        session = self.user_sessions.get(user_id, {})
        return bool(self.wager_dump_manager.get_wager_dump(user_id))

    async def _handle_admin_actions(self, query, context, values):
        """Handle admin-specific actions"""
        action = values[0] if values else 'menu'
        
        if action == 'menu':
            await query.edit_message_text(
                "🛠️ Admin Panel", 
                reply_markup=get_markup('admin_menu')
            )
        elif action == 'users':
            await query.edit_message_text(
                "👤 User Management", 
                reply_markup=get_markup('user_management')
            )
        elif action == 'stats':
            await self._show_admin_stats(query)
        elif action in ['verify', 'block', 'unblock']:
            context.user_data['admin_action'] = action
            await query.edit_message_text(
                f"Enter user ID to {action}:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="admin:users")
                ]])
            )

    async def handle_menu(self, query, context, values):
        """Handle main menu navigation"""
        user_id = query.from_user.id
        menu_action = values[0] if values else 'main'
        show_build_parlay = self.should_show_build_parlay(user_id)
        
        if menu_action == 'leagues':
            self.user_sessions[user_id] = {
                'league': None,
                'accumulated_results': self.user_sessions.get(user_id, {}).get('accumulated_results', []),
                'current_selections': [],
                'wager_dump': self.user_sessions.get(user_id, {}).get('wager_dump', [])  # Preserve wager dump
            }
            await query.edit_message_text(
                "⚽ Select a league:", 
                reply_markup=get_markup('league_selector')
            )
        elif menu_action == 'help':
            await self.show_help(query, context)
        elif menu_action == 'main':
            await query.edit_message_text(
                "🏠 Main Menu", 
                reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
            )
        elif menu_action == 'refresh':
            await self._handle_refresh(query, context)

    async def handle_action(self, query, context, values):
        """Handle general actions"""
        user_id = query.from_user.id
        show_build_parlay = self.should_show_build_parlay(user_id)
        action_type = values[0] if values else None
        
        if action_type == 'refresh':
            await self._handle_refresh(query, context)
        else:
            await self.show_error(
                query, 
                "Invalid action", 
                show_build_parlay=show_build_parlay
            )

    async def handle_league_selection(self, query, context, values):
        """Handle league selection"""
        user_id = query.from_user.id
        league_key = values[0] if values else None
        
        if not league_key or not self.league_manager.is_valid(league_key):
            return await self.show_error(query, "Invalid league")
        
        self.user_sessions.setdefault(user_id, {}).update({
            'league': league_key,
            'current_selections': []
        })
        
        if 'accumulated_results' not in self.user_sessions[user_id]:
            self.user_sessions[user_id]['accumulated_results'] = []
        
        await query.edit_message_text(
            f"✅ Selected: {self.league_manager.get_display_name(league_key)}\nChoose analysis method:",
            reply_markup=get_markup('algorithm_selector', paid_user=self.user_manager.is_paid(user_id))
        )

    async def handle_algorithm_selection(self, query, context, values):
        """Handle algorithm selection and process results"""
        user_id = query.from_user.id
        
        if not values:
            return await self.show_error(query, "No algorithm selected")
        
        algorithm = values[0].lower()
        
        if not (session := self.user_sessions.get(user_id)):
            return await self.show_error(query, "Session expired")
        
        league_key = session.get('league')
        if not league_key:
            return await self.show_error(query, "No league selected")
        
        try:
            api_league_key = self.league_manager.get_api_key(league_key)
            if not api_league_key:
                raise ValueError("Invalid league mapping")
            
            progress_msg = await query.edit_message_text(
                f"⚙️ Processing {self.league_manager.get_display_name(league_key)}...\nAlgorithm: {algorithm.upper()}"
            )
            
            results = await process_pipeline(
                api_key=SCRAPING_API_KEY,
                base_url=SCRAPING_BASE_URL,
                league_key=api_league_key,
                algorithm=algorithm,
                paid_user=self.user_manager.is_paid(user_id)
            )
            
            if 'error' in results:
                await self.show_error(query, f"Analysis failed: {results['error']}")
                return
            
            formatted = format_results(results)
            selections = []
            def safe_get(item, key, default="N/A"):
                return item.get(key, default) or default
            
            if algorithm == 'demo':
                for item in results.get('demo', []):
                    match = safe_get(item, 'match', 'N/A vs N/A')
                    home_team, away_team = match.split(' vs ') if ' vs ' in match else ('N/A', 'N/A')
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': home_team,
                        'away_team': away_team,
                        'market': 'match_winner',  # Demo is explicitly match_winner
                        'selection': safe_get(item, 'prediction'),
                        'odds': float(safe_get(item, 'odds', 1.5)),
                        'team_type': (
                            'home' if safe_get(item, 'prediction') == home_team
                            else 'away' if safe_get(item, 'prediction') == away_team
                            else 'draw' if safe_get(item, 'prediction', '').lower() == 'draw'
                            else 'unknown'
                        ),
                        'algorithm': 'demo'
                    })
            
            elif algorithm == 'arima':
                for item in results.get('arima', {}).values():
                    selection = safe_get(item, 'recommended_team')
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': safe_get(item, 'home_team'),
                        'away_team': safe_get(item, 'away_team'),
                        'market': safe_get(item, 'recommended_market'),  # Keep original market
                        'selection': selection,
                        'odds': float(safe_get(item, 'current_odds', 1.0)),
                        'team_type': (
                            'home' if selection == safe_get(item, 'home_team')
                            else 'away' if selection == safe_get(item, 'away_team')
                            else 'draw' if selection.lower() == 'draw'
                            else 'unknown'
                        ),
                        'algorithm': 'arima'
                    })
            
            elif algorithm == 'monte':
                for item in results.get('simulation_results', []):
                    selection = safe_get(item, 'team')
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': safe_get(item, 'home_team'),
                        'away_team': safe_get(item, 'away_team'),
                        'market': safe_get(item, 'market'),  # Keep original market
                        'selection': selection,
                        'odds': float(safe_get(item, 'odds', 1.0)),
                        'team_type': (
                        'home' if selection == safe_get(item, 'home_team')
                        else 'away' if selection == safe_get(item, 'away_team')  # Fixed to check away_team
                        else 'draw' if selection.lower() == 'draw'
                        else 'unknown'
                    ),
                        'algorithm': 'monte'
                    })
            
            # Add these cases to the existing algorithm selection handler
            elif algorithm == 'ocm':  # Odds Comparison Model
                for item in results.get('value_bets', []):
                    selection = safe_get(item, 'value_rating').split(' ')[-1].lower()
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': safe_get(item, 'home_team'),
                        'away_team': safe_get(item, 'away_team'),
                        'market': 'match_winner',
                        'selection': safe_get(item, 'home_team') if selection == 'home' else safe_get(item, 'away_team'),
                        'odds': float(safe_get(item, f'best_{selection}_odds', 1.5)),
                        'team_type': selection,
                        'algorithm': 'ocm'
                    })

            elif algorithm == 'kelly':  # Kelly Criterion
                for item in results.get('recommended_parlays', []):
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': safe_get(item, 'home_team'),
                        'away_team': safe_get(item, 'away_team'),
                        'market': safe_get(item, 'market', 'match_winner'),
                        'selection': safe_get(item, 'team', 'N/A'),
                        'odds': float(safe_get(item, 'odds', 1.0)),
                        'team_type': 'home' if safe_get(item, 'team') == safe_get(item, 'home_team') else 'away',
                        'algorithm': 'kelly'
                    })

            elif algorithm == 'ipt':  # Implied Probability Threshold
                for item in results.get('predictions', []):
                    if item['prediction'] == 'No Clear Favorite':
                        continue
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': safe_get(item, 'home_team'),
                        'away_team': safe_get(item, 'away_team'),
                        'market': 'match_winner',
                        'selection': safe_get(item, 'prediction').replace(' Win', ''),
                        'odds': 1/float(item['home_prob']) if 'Home' in item['prediction'] else 1/float(item['away_prob']),
                        'team_type': 'home' if 'Home' in item['prediction'] else 'away',
                        'algorithm': 'ipt'
                    })

            elif algorithm == 'dfs':  # Arbitrage Detection
                for item in results.get('arbitrage_opportunities', []):
                    # Add all three possible outcomes as separate selections
                    for outcome in ['home', 'away', 'draw']:
                        selections.append({
                            'league': safe_get(item, 'league', 'Unknown'),
                            'home_team': safe_get(item, 'home_team'),
                            'away_team': safe_get(item, 'away_team'),
                            'market': 'match_winner',
                            'selection': safe_get(item, f'{outcome}_team'),
                            'odds': float(item[f'{outcome}_odds']),
                            'team_type': outcome,
                            'algorithm': 'dfs'
                        })
            
            elif algorithm == 'value':
                for item in results.get('value_bets', []):
                    selection = safe_get(item, 'recommended_team', 'N/A')
                    selections.append({
                        'league': safe_get(item, 'league', 'Unknown'),
                        'home_team': safe_get(item, 'home_team'),
                        'away_team': safe_get(item, 'away_team'),
                        'market': safe_get(item, 'recommended_market'),  # Keep original market
                        'selection': selection,
                        'odds': float(safe_get(item, 'best_odds', 1.0)),
                        'team_type': (
                            'home' if selection == safe_get(item, 'home_team')
                            else 'away' if selection == safe_get(item, 'away_team')
                            else 'draw' if selection.lower() == 'draw'
                            else 'unknown'
                        ),
                        'algorithm': 'value'
                    })
            
            self.user_sessions[user_id]['current_selections'] = selections
            
            if not self.wager_dump_manager.verify_league_alg_result(user_id):
                await self.show_error(query, "No valid selections found")
                return
            
            await progress_msg.edit_text(
                f"🏆 {self.league_manager.get_display_name(league_key)} Results\n📊 Method: {algorithm.upper()}\n\n{formatted}",
                reply_markup=get_markup('wager_dump_actions')
            )
        
        except ValueError as e:
            logger.error(f"ValueError in algorithm selection: {str(e)}", exc_info=True)
            await self.show_error(query, f"Invalid league: {str(e)}")
        
        except Exception as e:
            logger.error(f"Algorithm error: {str(e)}", exc_info=True)
            await self.show_error(query, f"Analysis failed: {str(e)}")
        
    async def handle_pdf_strategy(self, query, context, values):
        """Handle PDF strategy selection"""
        user_id = query.from_user.id
        
        context.user_data['selected_markets'] = set()
        
        await query.edit_message_text(
            "📊 PDF Strategy Builder\n\nSelect markets to analyze:",
            reply_markup=get_markup('market_selector')
        )

    async def handle_market_selection(self, query, context, values):
        """Handle market selection for PDF strategy"""
        user_id = query.from_user.id
        market = values[0] if values else None
        
        if not market:
            return await self.show_error(query, "Invalid market")
        
        selected_markets = context.user_data.get('selected_markets', set())
        
        if market in selected_markets:
            selected_markets.remove(market)
        else:
            selected_markets.add(market)
        
        context.user_data['selected_markets'] = selected_markets
        
        await query.edit_message_text(
            f"📊 Selected Markets: {len(selected_markets)}\n\nChoose markets to analyze:",
            reply_markup=get_markup('market_selector', selected=selected_markets)
        )

    async def build_parlay(self, query, context):
        """Build optimized parlay from wager dump selections"""
        user_id = query.from_user.id
        wager_dump = self.wager_dump_manager.get_wager_dump(user_id)
        
        if not wager_dump:
            await query.edit_message_text(
                "❌ No selections available in wager dump.",
                reply_markup=get_markup('main_menu', show_build_parlay=False)
            )
            return
        
        await query.edit_message_text("🔍 Building optimal parlay...")
        
        # Use SmartParlayBuilder to generate the parlay
        builder = SmartParlayBuilder()
        parlay_combination = builder.generate_parlay(wager_dump)
        
        if not parlay_combination.selections:
            await query.edit_message_text(
                "❌ Could not build a suitable parlay.",
                reply_markup=get_markup('main_menu', show_build_parlay=False)
            )
            return
        
        parlay_text = "🎯 **Optimal Parlay**\n\n"
        for idx, selection in enumerate(parlay_combination.selections, 1):
            parlay_text += (
                f"{idx}. {selection.get('home_team')} vs {selection.get('away_team')}\n"
                f"   {selection.get('selection')} @ {selection.get('odds'):.2f}\n\n"
            )
        parlay_text += (
            f"**Total Odds:** {parlay_combination.total_odds:.2f}\n\n"
            f"Recommended stake: $10"
        )
        
        await query.edit_message_text(
            parlay_text,
            parse_mode="Markdown",
            reply_markup=get_markup('parlay_actions')
        )

    async def show_error(self, query, message, show_build_parlay=False):
        """Show error message and return to main menu"""
        await query.edit_message_text(
            f"❌ Error: {message}",
            reply_markup=get_markup('main_menu', show_build_parlay=show_build_parlay)
        )

    async def _show_admin_stats(self, query):
        """Show admin statistics"""
        total_users = len(self.user_manager.get_all_users())
        paid_users = len(self.user_manager.get_paid_users())
        blocked_users = len(self.user_manager.get_blocked_users())
        
        stats_text = (
            "📊 **Bot Statistics**\n\n"
            f"Total Users: {total_users}\n"
            f"Paid Users: {paid_users}\n"
            f"Blocked Users: {blocked_users}\n\n"
            "Active since: 2023-01-15"
        )
        
        await query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="admin:menu")
            ]])
        )

def run():
    """Run the bot"""
    init_db()  # Initialize database
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    bot = BetSageAIBot()
    
    application.add_handler(CommandHandler("start", bot.handle_start))
    application.add_handler(CommandHandler("pay", bot.handle_payment))
    application.add_handler(CommandHandler("verify", bot.verify_payment))
    application.add_handler(CommandHandler("block", bot.block_user))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == "__main__":
    run()