
import discord
from discord import app_commands
from discord.ext import commands
import traceback
from typing import Optional, Literal

from utils import logger

class Management(commands.Cog):
    """Cog for bot management commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_commands(self, ctx: commands.Context, scope: Optional[Literal["global", "guild"]] = "guild"):
        """Sync application commands
        
        Args:
            scope: Whether to sync globally or only to the current guild
        """
        try:
            if scope == "global":
                # Sync commands globally (takes up to an hour to propagate)
                synced = await self.bot.tree.sync()
                await ctx.send(f"Synced {len(synced)} commands globally")
            else:
                # Sync to current guild (instant)
                guild = ctx.guild
                self.bot.tree.copy_global_to(guild=guild)
                synced = await self.bot.tree.sync(guild=guild)
                await ctx.send(f"Synced {len(synced)} commands to this guild")
            
            logger.info(f"Synced commands: {scope} scope")
            
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            await ctx.send(f"Failed to sync commands: {e}")
            traceback.print_exc()
    
    @commands.command(name="status")
    @commands.is_owner()
    async def status(self, ctx: commands.Context):
        """Check bot status"""
        embed = discord.Embed(title="ChessBot Status", color=discord.Color.blue())
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(sum(guild.member_count for guild in self.bot.guilds)), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        # Get uptime
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(self.bot.uptime)
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        
        embed.add_field(name="Uptime", value=f"{days}d {hours}h {minutes}m {seconds}s", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Management(bot))
