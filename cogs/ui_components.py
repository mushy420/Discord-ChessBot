
import discord
from discord import ui
import asyncio
from typing import Optional, Callable, Any, Coroutine

class ChallengeButtons(ui.View):
    """View with buttons for chess challenge responses"""
    
    def __init__(self, challenger, challenged, timeout=300):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.challenged = challenged
        self.response = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interacting user is the challenged player"""
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message(
                "Only the challenged player can respond to this challenge", 
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: ui.Button):
        """Accept the challenge"""
        self.response = True
        self.stop()
        await interaction.response.defer()
    
    @ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: ui.Button):
        """Decline the challenge"""
        self.response = False
        self.stop()
        await interaction.response.defer()
    
    async def on_timeout(self):
        """Handle view timeout"""
        self.response = None
        self.stop()
