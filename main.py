import discord
from discord import app_commands
from discord.ext import commands
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
        activity=discord.Game(name="Chess | /chess help")
    )
    
    # Register chess commands
    setup_chess_commands(bot)
    logger.info("Chess commands registered")
    
    # Sync commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors"""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", 
            ephemeral=True
        )
        return
    
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to use this command.", 
            ephemeral=True
        )
        return
    
    # Log unexpected errors
    logger.error(f"Command error in {interaction.command}: {str(error)}")
    logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
    
    # Notify user
    error_message = str(error) or "An unknown error occurred"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(f"Error executing command: {error_message}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error executing command: {error_message}", ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

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
