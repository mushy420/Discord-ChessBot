
import discord
from discord.ext import commands
import asyncio
import chess
from typing import Dict, List, Optional, Tuple, Union
import time
import re
import os

from chess_engine import GameManager, ChessGame
from ui_renderer import ChessEmbedRenderer
from utils import logger, CooldownManager, send_with_retry, format_exception

class ChessCommands(commands.Cog):
    """Chess game commands for Discord"""
    
    def __init__(self, bot):
        """Initialize chess commands"""
        self.bot = bot
        self.game_manager = GameManager()
        self.embed_renderer = ChessEmbedRenderer()
        self.cooldown_manager = CooldownManager()
        self.active_challenges = {}  # channel_id -> (message_id, challenger_id, challenged_id, expire_time)
        
        # Start background task for cleaning up stale games and challenges
        self.cleanup_task = asyncio.create_task(self.cleanup_loop())
        logger.info("Chess commands initialized")
    
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        # Cancel background task
        if self.cleanup_task:
            self.cleanup_task.cancel()
    
    async def cleanup_loop(self):
        """Background task to clean up stale games and challenges"""
        try:
            while True:
                # Clean up stale games every hour
                self.game_manager.cleanup_stale_games(max_inactive_time=3600)
                
                # Clean up expired challenges
                current_time = time.time()
                expired_challenges = []
                
                for channel_id, (message_id, challenger_id, challenged_id, expire_time) in self.active_challenges.items():
                    if current_time > expire_time:
                        expired_challenges.append(channel_id)
                        
                        # Try to edit the message to show it expired
                        try:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                message = await channel.fetch_message(message_id)
                                if message:
                                    embed = message.embeds[0]
                                    embed.description = "This challenge has expired."
                                    embed.color = discord.Color.dark_grey()
                                    await message.edit(embed=embed)
                        except Exception as e:
                            logger.warning(f"Could not edit expired challenge message: {str(e)}")
                
                # Remove expired challenges
                for channel_id in expired_challenges:
                    self.active_challenges.pop(channel_id, None)
                
                # Sleep for a minute before next check
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {str(e)}")
    
    @commands.group(name="chess", invoke_without_command=True)
    async def chess(self, ctx):
        """Main chess command group"""
        await self.show_help(ctx)
    
    @chess.command(name="help")
    async def show_help(self, ctx):
        """Show help information"""
        embed = await self.embed_renderer.render_help_embed()
        await ctx.send(embed=embed)
    
    @chess.command(name="challenge")
    async def challenge(self, ctx, opponent: discord.Member = None):
        """Challenge a user to a chess game"""
        if self.cooldown_manager.is_on_cooldown(ctx.author.id, "challenge", 10):
            cooldown = self.cooldown_manager.get_remaining_cooldown(ctx.author.id, "challenge")
            await ctx.send(f"Please wait {cooldown:.1f} seconds before issuing another challenge.")
            return
        
        try:
            # Check if opponent is valid
            if not opponent:
                await ctx.send("You need to specify an opponent to challenge. Example: `!chess challenge @user`")
                return
                
            if opponent.id == ctx.author.id:
                await ctx.send("You can't challenge yourself to a game.")
                return
                
            if opponent.bot:
                await ctx.send("You can't challenge a bot to a game.")
                return
            
            # Check if already in a game in this channel
            existing_game = self.game_manager.get_player_game(ctx.author.id, ctx.channel.id)
            if existing_game:
                await ctx.send("You are already in a game in this channel. Finish or resign that game first.")
                return
                
            # Check if there's already an active challenge in this channel
            if ctx.channel.id in self.active_challenges:
                await ctx.send("There's already an active challenge in this channel. Wait for it to be accepted, declined, or expire.")
                return
            
            # Create and send challenge embed
            challenge_embed = await self.embed_renderer.render_challenge_embed(ctx.author, opponent)
            challenge_message = await ctx.send(embed=challenge_embed)
            
            # Add reactions for accepting/declining
            await challenge_message.add_reaction("✅")
            await challenge_message.add_reaction("❌")
            
            # Store challenge data with 5-minute expiration
            expire_time = time.time() + 300  # 5 minutes
            self.active_challenges[ctx.channel.id] = (challenge_message.id, ctx.author.id, opponent.id, expire_time)
            
            # Set up reaction listeners
            def check(reaction, user):
                return (
                    reaction.message.id == challenge_message.id and 
                    user.id == opponent.id and
                    str(reaction.emoji) in ["✅", "❌"]
                )
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
                
                # Remove from active challenges
                self.active_challenges.pop(ctx.channel.id, None)
                
                if str(reaction.emoji) == "✅":
                    # Challenge accepted
                    await self.start_game(ctx.channel, ctx.author, opponent)
                else:
                    # Challenge declined
                    decline_embed = discord.Embed(
                        title="Chess Challenge Declined", 
                        description=f"{opponent.mention} has declined the chess challenge.", 
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=decline_embed)
                    
                    # Update the original challenge message
                    challenge_embed.description = f"{ctx.author.mention}'s challenge to {opponent.mention} was declined."
                    challenge_embed.color = discord.Color.red()
                    await challenge_message.edit(embed=challenge_embed)
                    
            except asyncio.TimeoutError:
                # Challenge expired
                self.active_challenges.pop(ctx.channel.id, None)
                
                try:
                    # Update the original challenge message if it still exists
                    challenge_embed.description = f"{ctx.author.mention}'s challenge to {opponent.mention} has expired."
                    challenge_embed.color = discord.Color.dark_grey()
                    await challenge_message.edit(embed=challenge_embed)
                except Exception:
                    pass
        
        except Exception as e:
            logger.error(f"Error in challenge command: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    async def start_game(self, channel, white_player, black_player):
        """Start a new chess game between two players"""
        try:
            # Create a new game
            game = self.game_manager.create_game(white_player.id, black_player.id, channel.id)
            
            # Render and send the initial board
            embed, file = await self.embed_renderer.render_game_embed(
                game, white_user=white_player, black_user=black_player, bot=self.bot
            )
            
            start_message = await channel.send(
                content=f"Game started! {white_player.mention} (White) vs {black_player.mention} (Black)",
                embed=embed,
                file=file
            )
            
            # Store the message ID for future updates
            game.last_message_id = start_message.id
            
            # Send instructions
            await channel.send(
                f"{white_player.mention}'s turn. Make a move using `!chess move <move>` "
                "(e.g., `!chess move e4` or `!chess move e2e4`)"
            )
            
            return game
            
        except Exception as e:
            logger.error(f"Error starting game: {str(e)}")
            await channel.send(f"Error starting game: {format_exception(e)}")
            return None
    
    @chess.command(name="move")
    async def make_move(self, ctx, *, move_str: str = None):
        """Make a move in the current game"""
        try:
            if not move_str:
                await ctx.send("Please specify a move. Example: `!chess move e4` or `!chess move e2e4`")
                return
                
            # Find the current game in this channel
            game = self.game_manager.get_game_by_channel(ctx.channel.id)
            
            if not game:
                await ctx.send("There is no active chess game in this channel. Start one with `!chess challenge @user`")
                return
                
            # Check if it's the player's turn
            if not game.is_player_turn(ctx.author.id):
                current_player_id = game.current_player_id
                try:
                    current_player = await self.bot.fetch_user(current_player_id)
                    await ctx.send(f"It's not your turn. Waiting for {current_player.mention} to move.")
                except Exception:
                    await ctx.send(f"It's not your turn. Waiting for the other player to move.")
                return
            
            # Make the move
            success, message = game.make_move(move_str)
            
            if not success:
                await ctx.send(f"Invalid move: {message}")
                return
            
            # Get the players
            white_user = await self.bot.fetch_user(game.white_id)
            black_user = await self.bot.fetch_user(game.black_id)
            
            # Render the updated board
            embed, file = await self.embed_renderer.render_game_embed(
                game, white_user=white_user, black_user=black_user, bot=self.bot
            )
            
            # Send the updated board
            move_message = await ctx.send(embed=embed, file=file)
            game.last_message_id = move_message.id
            
            # Notify about status
            if message:  # Status message from the move (checkmate, etc.)
                await ctx.send(message)
                
                if game.status == "finished":
                    # Game is over, send final message
                    if game.result == "white_win":
                        await ctx.send(f"{white_user.mention} (White) wins! Game over.")
                    elif game.result == "black_win":
                        await ctx.send(f"{black_user.mention} (Black) wins! Game over.")
                    else:
                        await ctx.send("Game ended in a draw!")
                        
                    # Include PGN
                    pgn = game.get_pgn()
                    await ctx.send(f"Game PGN:\n```{pgn}```")
            
            # If game continues, notify next player
            if game.status == "active":
                next_player_id = game.current_player_id
                next_player = await self.bot.fetch_user(next_player_id)
                await ctx.send(f"{next_player.mention}'s turn. Make a move using `!chess move <move>`")
        
        except Exception as e:
            logger.error(f"Error making move: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    @chess.command(name="board")
    async def show_board(self, ctx):
        """Show the current board state"""
        try:
            # Find the current game in this channel
            game = self.game_manager.get_game_by_channel(ctx.channel.id)
            
            if not game:
                await ctx.send("There is no active chess game in this channel. Start one with `!chess challenge @user`")
                return
            
            # Get the players
            white_user = await self.bot.fetch_user(game.white_id)
            black_user = await self.bot.fetch_user(game.black_id)
            
            # Render the board
            embed, file = await self.embed_renderer.render_game_embed(
                game, white_user=white_user, black_user=black_user, bot=self.bot
            )
            
            # Send the board
            await ctx.send(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Error showing board: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    @chess.command(name="resign")
    async def resign_game(self, ctx):
        """Resign from the current game"""
        try:
            # Find the player's game in this channel
            game = self.game_manager.get_player_game(ctx.author.id, ctx.channel.id)
            
            if not game:
                await ctx.send("You are not in an active chess game in this channel.")
                return
            
            # Resign the game
            result = self.game_manager.resign_game(game.game_id, ctx.author.id)
            
            if not result:
                await ctx.send("Failed to resign the game.")
                return
            
            # Get the players
            white_user = await self.bot.fetch_user(game.white_id)
            black_user = await self.bot.fetch_user(game.black_id)
            
            # Determine winner
            if ctx.author.id == game.white_id:
                winner = black_user
                winner_color = "Black"
            else:
                winner = white_user
                winner_color = "White"
            
            # Send resign message
            await ctx.send(f"{ctx.author.mention} has resigned. {winner.mention} ({winner_color}) wins!")
            
            # Render final board
            embed, file = await self.embed_renderer.render_game_embed(
                game, white_user=white_user, black_user=black_user, bot=self.bot
            )
            
            # Send the final board
            await ctx.send(embed=embed, file=file)
            
            # Include PGN
            pgn = game.get_pgn()
            await ctx.send(f"Game PGN:\n```{pgn}```")
            
        except Exception as e:
            logger.error(f"Error resigning game: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    @chess.command(name="pgn")
    async def show_pgn(self, ctx):
        """Show the PGN of the current game"""
        try:
            # Find the current game in this channel
            game = self.game_manager.get_game_by_channel(ctx.channel.id)
            
            if not game:
                await ctx.send("There is no active chess game in this channel.")
                return
            
            # Get the PGN
            pgn = game.get_pgn()
            
            # Send the PGN
            await ctx.send(f"Game PGN:\n```{pgn}```")
            
        except Exception as e:
            logger.error(f"Error showing PGN: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    @chess.command(name="suggest")
    async def suggest_move(self, ctx):
        """Suggest moves for the current position"""
        try:
            # Find the current game in this channel
            game = self.game_manager.get_game_by_channel(ctx.channel.id)
            
            if not game:
                await ctx.send("There is no active chess game in this channel.")
                return
            
            # Check if it's the player's turn
            if not game.is_player_turn(ctx.author.id):
                await ctx.send("It's not your turn. You can only get suggestions on your turn.")
                return
            
            # Get move suggestions
            suggestions = game.get_move_suggestions(count=3)
            
            if not suggestions:
                await ctx.send("No move suggestions available.")
                return
            
            # Format suggestions
            suggestions_text = "Suggested moves:\n"
            for i, (move, eval_score) in enumerate(suggestions):
                suggestions_text += f"{i+1}. **{move}** (Evaluation: {eval_score:.2f})\n"
            
            await ctx.send(suggestions_text)
            
        except Exception as e:
            logger.error(f"Error suggesting move: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    @chess.command(name="analyze")
    async def analyze_position(self, ctx):
        """Analyze the current position"""
        try:
            # Find the current game in this channel
            game = self.game_manager.get_game_by_channel(ctx.channel.id)
            
            if not game:
                await ctx.send("There is no active chess game in this channel.")
                return
            
            # Get move suggestions for analysis
            suggestions = game.get_move_suggestions(count=3)
            
            # Create analysis embed
            analysis_embed = await self.embed_renderer.render_analysis_embed(game, suggestions)
            
            # Send the analysis
            await ctx.send(embed=analysis_embed)
            
        except Exception as e:
            logger.error(f"Error analyzing position: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
    
    @chess.command(name="explain")
    async def explain_position(self, ctx):
        """Explain the current position"""
        try:
            # Find the current game in this channel
            game = self.game_manager.get_game_by_channel(ctx.channel.id)
            
            if not game:
                await ctx.send("There is no active chess game in this channel.")
                return
            
            # Get the board state
            board = game.board
            
            # Basic position explanation
            explanation = []
            
            # Game phase
            move_count = len(game.move_history)
            if move_count < 10:
                explanation.append("**Opening phase**: Focus on developing pieces, controlling the center, and king safety.")
            elif move_count < 30:
                explanation.append("**Middlegame phase**: Focus on creating and executing plans, tactical opportunities, and piece coordination.")
            else:
                explanation.append("**Endgame phase**: Focus on pawn promotion, king activity, and simplification if ahead in material.")
            
            # Material count
            white_material = sum(len(list(board.pieces(piece_type, chess.WHITE))) * value 
                               for piece_type, value in [(chess.PAWN, 1), (chess.KNIGHT, 3), 
                                                        (chess.BISHOP, 3), (chess.ROOK, 5), 
                                                        (chess.QUEEN, 9)])
            
            black_material = sum(len(list(board.pieces(piece_type, chess.BLACK))) * value 
                               for piece_type, value in [(chess.PAWN, 1), (chess.KNIGHT, 3), 
                                                        (chess.BISHOP, 3), (chess.ROOK, 5), 
                                                        (chess.QUEEN, 9)])
            
            material_diff = white_material - black_material
            if material_diff > 2:
                explanation.append(f"**Material**: White is ahead by {material_diff} points.")
            elif material_diff < -2:
                explanation.append(f"**Material**: Black is ahead by {abs(material_diff)} points.")
            else:
                explanation.append("**Material**: Material is roughly equal.")
            
            # King safety
            white_king_square = board.king(chess.WHITE)
            black_king_square = board.king(chess.BLACK)
            white_king_attackers = len(list(board.attackers(chess.BLACK, white_king_square))) if white_king_square else 0
            black_king_attackers = len(list(board.attackers(chess.WHITE, black_king_square))) if black_king_square else 0
            
            if white_king_attackers > 0:
                explanation.append(f"**King Safety**: White's king is under attack by {white_king_attackers} piece(s).")
            if black_king_attackers > 0:
                explanation.append(f"**King Safety**: Black's king is under attack by {black_king_attackers} piece(s).")
            
            # Mobility
            if board.turn:
                # White to move
                mobility = len(list(board.legal_moves))
                if mobility > 30:
                    explanation.append(f"**Mobility**: White has many options ({mobility} legal moves).")
                elif mobility < 10:
                    explanation.append(f"**Mobility**: White has limited options (only {mobility} legal moves).")
            else:
                # Black to move
                mobility = len(list(board.legal_moves))
                if mobility > 30:
                    explanation.append(f"**Mobility**: Black has many options ({mobility} legal moves).")
                elif mobility < 10:
                    explanation.append(f"**Mobility**: Black has limited options (only {mobility} legal moves).")
            
            # Pawn structure
            white_pawns = list(board.pieces(chess.PAWN, chess.WHITE))
            black_pawns = list(board.pieces(chess.PAWN, chess.BLACK))
            
            white_pawn_files = [chess.square_file(square) for square in white_pawns]
            black_pawn_files = [chess.square_file(square) for square in black_pawns]
            
            # Count doubled pawns
            white_doubled = len(white_pawn_files) - len(set(white_pawn_files))
            black_doubled = len(black_pawn_files) - len(set(black_pawn_files))
            
            if white_doubled > 0:
                explanation.append(f"**Pawn Structure**: White has {white_doubled} doubled pawn(s).")
            if black_doubled > 0:
                explanation.append(f"**Pawn Structure**: Black has {black_doubled} doubled pawn(s).")
            
            # Send the explanation
            await ctx.send("**Position Analysis**\n\n" + "\n".join(explanation))
            
        except Exception as e:
            logger.error(f"Error explaining position: {str(e)}")
            await ctx.send(f"An error occurred: {format_exception(e)}")
