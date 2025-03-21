
import discord
from discord.ext import commands
from discord.ext import tasks
import asyncio
import os
from dotenv import load_dotenv
import logging
import sys
import traceback
from typing import Dict, List, Optional

from utils import setup_logging, logger
from bot_commands import setup_chess_commands

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
AI_DIFFICULTY = int(os.getenv("AI_DIFFICULTY", 5))

# Verify token is available
if not TOKEN:
    logger.critical("No Discord token found in .env file. Please add your bot token as DISCORD_TOKEN=your_token")
    sys.exit(1)

# Configure bot with intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content
intents.members = True  # Needed to access member information

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Set bot activity
    await bot.change_presence(
        activity=discord.Game(name="Chess | !chess help")
    )
    
    # Register chess commands
    setup_chess_commands(bot)
    logger.info("Chess commands registered")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}. Use `!chess help` for command usage.")
        return
    
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument: {str(error)}. Use `!chess help` for command usage.")
        return
    
    # Log unexpected errors
    logger.error(f"Command error in {ctx.command}: {str(error)}")
    logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
    
    # Notify user
    error_message = str(error) or "An unknown error occurred"
    await ctx.send(f"Error executing command: {error_message}")

def run_bot():
    """Run the bot"""
    try:
        logger.info("Starting ChessBot...")
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("Invalid Discord token. Please check your .env file.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Error starting bot: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    logger.info("ChessBot initializing...")
    run_bot()
