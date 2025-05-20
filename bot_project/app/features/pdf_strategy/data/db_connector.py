from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from typing import Iterator
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles database operations with proper session management"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory

    @contextmanager
    def session_scope(self) -> Iterator[None]:
        """Transactional scope with automatic cleanup"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_matches_with_odds(self, days_ahead: int = 3) -> list[dict]:
        """Safe parameterized query for SQLite"""
        query = text("""
            SELECT m.id, m.league, o.home_odds, m.match_date, m.is_cup
            FROM matches m
            JOIN odds o ON m.id = o.match_id
            WHERE m.match_date >= DATE('now')
            AND m.match_date <= DATE('now', :days_offset)
            ORDER BY m.match_date ASC
        """)
        
        try:
            with self.session_scope() as session:
                result = session.execute(
                    query, 
                    {'days_offset': f'+{days_ahead} days'}
                )
                return [dict(row._mapping) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Query failed: {str(e)}")
            return []