
import os
import logging
import colorlog
import json
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional, Callable, Coroutine

# Configure logging with color formatting
def setup_logging():
    """Set up logging with color formatting and appropriate level from environment"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )
    
    logger = logging.getLogger('chessbot')
    logger.setLevel(getattr(logging, log_level))
    logger.addHandler(handler)
    
    # Also create a file handler for persistent logging
    file_handler = logging.FileHandler("chessbot.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# Game data persistence
class GameStorage:
    """Handles persistence of game data between bot restarts"""
    
    def __init__(self, filename="games.json"):
        self.filename = filename
        self.games = {}
        self.load()
    
    def load(self):
        """Load game data from disk"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.games = json.load(f)
                logger.info(f"Loaded {len(self.games)} games from storage")
            else:
                logger.info("No game storage file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading game data: {str(e)}")
            self.games = {}
    
    def save(self):
        """Save game data to disk"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.games, f)
            logger.info(f"Saved {len(self.games)} games to storage")
        except Exception as e:
            logger.error(f"Error saving game data: {str(e)}")
    
    def add_game(self, game_id, game_data):
        """Add or update a game in storage"""
        self.games[game_id] = game_data
        self.save()
    
    def get_game(self, game_id):
        """Retrieve a game from storage"""
        return self.games.get(game_id)
    
    def remove_game(self, game_id):
        """Remove a game from storage"""
        if game_id in self.games:
            del self.games[game_id]
            self.save()
    
    def get_all_games(self):
        """Get all stored games"""
        return self.games

# Discord interaction helpers
async def send_with_retry(send_func: Callable[..., Coroutine], *args, **kwargs) -> Optional[Any]:
    """Attempt to send a Discord message with retries on failure"""
    max_retries = 3
    backoff_factor = 2
    
    for attempt in range(max_retries):
        try:
            return await send_func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                logger.warning(f"Message send failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed to send message after {max_retries} attempts: {str(e)}")
                return None

# Error handling helper
def format_exception(e: Exception) -> str:
    """Format an exception into a user-friendly message"""
    return f"Error: {type(e).__name__} - {str(e)}"

# User cooldown tracking
class CooldownManager:
    """Manages command cooldowns to prevent spam"""
    
    def __init__(self):
        self.cooldowns = {}
    
    def is_on_cooldown(self, user_id: int, command: str, cooldown_seconds: int) -> bool:
        """Check if a user is on cooldown for a command"""
        key = f"{user_id}:{command}"
        now = datetime.now().timestamp()
        
        if key in self.cooldowns:
            if now - self.cooldowns[key] < cooldown_seconds:
                return True
        
        self.cooldowns[key] = now
        return False

    def get_remaining_cooldown(self, user_id: int, command: str) -> float:
        """Get the remaining cooldown time in seconds"""
        key = f"{user_id}:{command}"
        now = datetime.now().timestamp()
        
        if key in self.cooldowns:
            elapsed = now - self.cooldowns[key]
            cooldown = self.cooldowns.get(f"{command}_time", 3)  # Default 3 seconds
            remaining = cooldown - elapsed
            return max(0, remaining)
        
        return 0
