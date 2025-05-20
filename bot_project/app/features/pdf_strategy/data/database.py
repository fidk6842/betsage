"""Database models and initialization"""
from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
from config.settings import DATABASE_URL   

logger = logging.getLogger(__name__)
Base = declarative_base()

class Match(Base):
    """Football match entity with cup status"""
    __tablename__ = 'matches'
    id = Column(String(36), primary_key=True)
    league = Column(String(50), nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    match_date = Column(DateTime, nullable=False, index=True)
    is_cup = Column(Boolean, default=False, nullable=False)

class Odd(Base):
    """Betting odds with referential integrity"""
    __tablename__ = 'odds'
    match_id = Column(String(36), ForeignKey('matches.id', ondelete='CASCADE'), primary_key=True)
    home_odds = Column(Float, nullable=False)
    draw_odds = Column(Float, nullable=False)
    away_odds = Column(Float, nullable=False)

def init_db():
    """Initialize database connection pool"""
    try:
        engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
        Base.metadata.create_all(engine)
        return scoped_session(sessionmaker(bind=engine, autocommit=False))
    except SQLAlchemyError as e:
        logger.critical(f"Database initialization failed: {str(e)}")
        raise

# Initialize the database session factory
Session = init_db()