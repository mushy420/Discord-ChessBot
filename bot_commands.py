import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
import asyncio
import chess
from typing import Dict, List, Optional, Tuple, Union
import time
import re
import os

from chess_engine import GameManager, ChessGame
from ui_renderer import ChessEmbedRenderer
from utils import logger, CooldownManager, send_with_retry, format_exception

# Define button classes for challenge responses
class ChallengeButtons(discord.ui.View):
    def __init__(self, challenger, challenged, timeout=300):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.challenged = challenged
        self.response = None
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("Only the challenged player can accept this game", ephemeral=True)
            return
        
        self.response = True
        self.stop()
        await interaction.response.defer()
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("Only the challenged player can respond to this challenge", ephemeral=True)
            return
        
        self.response = False
        self.stop()
        await interaction.response.defer()
    
    async def on_timeout(self):
        self.response = None
        self.stop()

def setup_chess_commands(bot):
    """Set up all chess commands for the bot"""
    game_manager = GameManager()
    embed_renderer = ChessEmbedRenderer()
    cooldown_manager = CooldownManager()
    active_challenges = {}  # channel_id -> challenger_id, challenged_id, expire_time
    
    # Start background task for cleaning up stale games and challenges
    @tasks.loop(minutes=5.0)
    async def cleanup_loop():
        """Background task to clean up stale games"""
        try:
            # Clean up stale games every 5 minutes
            stale_count = game_manager.cleanup_stale_games(max_inactive_time=3600)
            if stale_count > 0:
                logger.info(f"Cleaned up {stale_count} stale games")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {str(e)}")
    
    cleanup_loop.start()
    
    # Create a chess command group
    chess_group = app_commands.Group(name="chess", description="Commands for playing chess")
    
    @chess_group.command(name="help")
    async def chess_help(interaction: discord.Interaction):
        """Show help information for chess commands"""
        embed = await embed_renderer.render_help_embed()
        await interaction.response.send_message(embed=embed)
    
    @chess_group.command(name="challenge")
    @app_commands.describe(opponent="The player you want to challenge to a chess game")
    async def chess_challenge(interaction: discord.Interaction, opponent: discord.Member):
        """Challenge another user to a chess game"""
        if cooldown_manager.is_on_cooldown(interaction.user.id, "challenge", 10):
            cooldown = cooldown_manager.get_remaining_cooldown(interaction.user.id, "challenge")
            await interaction.response.send_message(
                f"Please wait {cooldown:.1f} seconds before issuing another challenge.",
                ephemeral=True
            )
            return
        
        try:
            # Check if opponent is valid
            if opponent.id == interaction.user.id:
                await interaction.response.send_message("You can't challenge yourself to a game.", ephemeral=True)
                return
                
            if opponent.bot:
                await interaction.response.send_message("You can't challenge a bot to a game.", ephemeral=True)
                return
            
            # Check if already in a game in this channel
            existing_game = game_manager.get_player_game(interaction.user.id, interaction.channel_id)
            if existing_game:
                await interaction.response.send_message(
                    "You are already in a game in this channel. Finish or resign that game first.",
                    ephemeral=True
                )
                return
                
            # Check if there's already an active challenge in this channel
            if interaction.channel_id in active_challenges:
                await interaction.response.send_message(
                    "There's already an active challenge in this channel. Wait for it to be accepted, declined, or expire.",
                    ephemeral=True
                )
                return
            
            # Create and send challenge embed with buttons
            challenge_embed = await embed_renderer.render_challenge_embed(interaction.user, opponent)
            
            # Create the button view
            view = ChallengeButtons(interaction.user, opponent)
            
            # Send the challenge message
            await interaction.response.send_message(
                f"{opponent.mention}, you've been challenged to a chess game by {interaction.user.mention}!",
                embed=challenge_embed,
                view=view
            )
            
            # Store challenge data with 5-minute expiration
            expire_time = time.time() + 300  # 5 minutes
            active_challenges[interaction.channel_id] = (interaction.user.id, opponent.id, expire_time)
            
            # Wait for the button response
            await view.wait()
            
            # Remove from active challenges
            active_challenges.pop(interaction.channel_id, None)
            
            # Handle the response
            if view.response is True:
                # Challenge accepted
                game = await start_game(interaction.channel, interaction.user, opponent)
                if game:
                    await interaction.followup.send(
                        f"Game started! {interaction.user.mention} (White) vs {opponent.mention} (Black)\n"
                        f"{interaction.user.mention}'s turn. Make a move using `/chess move`"
                    )
            elif view.response is False:
                # Challenge declined
                decline_embed = discord.Embed(
                    title="Chess Challenge Declined", 
                    description=f"{opponent.mention} has declined the chess challenge.", 
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=decline_embed)
            else:
                # Challenge expired
                await interaction.followup.send(
                    f"{interaction.user.mention}'s challenge to {opponent.mention} has expired.",
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Error in challenge command: {str(e)}")
            await interaction.followup.send(f"An error occurred: {format_exception(e)}")
    
    async def start_game(channel, white_player, black_player):
        """Start a new chess game between two players"""
        try:
            # Create a new game
            game = game_manager.create_game(white_player.id, black_player.id, channel.id)
            
            # Render and send the initial board
            embed, file = await embed_renderer.render_game_embed(
                game, white_user=white_player, black_user=black_player, bot=bot
            )
            
            start_message = await channel.send(
                embed=embed,
                file=file
            )
            
            # Store the message ID for future updates
            game.last_message_id = start_message.id
            
            return game
            
        except Exception as e:
            logger.error(f"Error starting game: {str(e)}")
            await channel.send(f"Error starting game: {format_exception(e)}")
            return None
    
    @chess_group.command(name="move")
    @app_commands.describe(move="Your chess move in algebraic notation (e.g., e4 or e2e4)")
    async def chess_move(interaction: discord.Interaction, move: str):
        """Make a move in the current chess game"""
        try:
            # Find the current game in this channel
            game = game_manager.get_game_by_channel(interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "There is no active chess game in this channel. Start one with `/chess challenge`",
                    ephemeral=True
                )
                return
                
            # Check if it's the player's turn
            if not game.is_player_turn(interaction.user.id):
                current_player_id = game.current_player_id
                try:
                    current_player = await bot.fetch_user(current_player_id)
                    await interaction.response.send_message(
                        f"It's not your turn. Waiting for {current_player.mention} to move.",
                        ephemeral=True
                    )
                except Exception:
                    await interaction.response.send_message(
                        f"It's not your turn. Waiting for the other player to move.",
                        ephemeral=True
                    )
                return
            
            # Acknowledge the command
            await interaction.response.defer()
            
            # Make the move
            success, message = game.make_move(move)
            
            if not success:
                await interaction.followup.send(f"Invalid move: {message}")
                return
            
            # Get the players
            white_user = await bot.fetch_user(game.white_id)
            black_user = await bot.fetch_user(game.black_id)
            
            # Render the updated board
            embed, file = await embed_renderer.render_game_embed(
                game, white_user=white_user, black_user=black_user, bot=bot
            )
            
            # Send the updated board
            move_message = await interaction.followup.send(embed=embed, file=file)
            
            # Update the last message ID if possible
            if hasattr(move_message, "id"):
                game.last_message_id = move_message.id
            
            # Notify about status
            if message:  # Status message from the move (checkmate, etc.)
                await interaction.channel.send(message)
                
                if game.status == "finished":
                    # Game is over, send final message
                    if game.result == "white_win":
                        await interaction.channel.send(f"{white_user.mention} (White) wins! Game over.")
                    elif game.result == "black_win":
                        await interaction.channel.send(f"{black_user.mention} (Black) wins! Game over.")
                    else:
                        await interaction.channel.send("Game ended in a draw!")
                        
                    # Include PGN
                    pgn = game.get_pgn()
                    await interaction.channel.send(f"Game PGN:\n```{pgn}```")
            
            # If game continues, notify next player
            if game.status == "active":
                next_player_id = game.current_player_id
                next_player = await bot.fetch_user(next_player_id)
                await interaction.channel.send(f"{next_player.mention}'s turn. Make a move using `/chess move`")
        
        except Exception as e:
            logger.error(f"Error making move: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send(f"An error occurred: {format_exception(e)}")
            else:
                await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    @chess_group.command(name="board")
    async def chess_board(interaction: discord.Interaction):
        """Show the current board state"""
        try:
            # Find the current game in this channel
            game = game_manager.get_game_by_channel(interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "There is no active chess game in this channel. Start one with `/chess challenge`",
                    ephemeral=True
                )
                return
            
            # Get the players
            white_user = await bot.fetch_user(game.white_id)
            black_user = await bot.fetch_user(game.black_id)
            
            # Render the board
            embed, file = await embed_renderer.render_game_embed(
                game, white_user=white_user, black_user=black_user, bot=bot
            )
            
            # Send the board
            await interaction.response.send_message(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Error showing board: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    @chess_group.command(name="resign")
    async def chess_resign(interaction: discord.Interaction):
        """Resign from the current game"""
        try:
            # Find the player's game in this channel
            game = game_manager.get_player_game(interaction.user.id, interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "You are not in an active chess game in this channel.",
                    ephemeral=True
                )
                return
            
            # Acknowledge the command
            await interaction.response.defer()
            
            # Resign the game
            result = game_manager.resign_game(game.game_id, interaction.user.id)
            
            if not result:
                await interaction.followup.send("Failed to resign the game.")
                return
            
            # Get the players
            white_user = await bot.fetch_user(game.white_id)
            black_user = await bot.fetch_user(game.black_id)
            
            # Determine winner
            if interaction.user.id == game.white_id:
                winner = black_user
                winner_color = "Black"
            else:
                winner = white_user
                winner_color = "White"
            
            # Send resign message
            await interaction.followup.send(f"{interaction.user.mention} has resigned. {winner.mention} ({winner_color}) wins!")
            
            # Render final board
            embed, file = await embed_renderer.render_game_embed(
                game, white_user=white_user, black_user=black_user, bot=bot
            )
            
            # Send the final board
            await interaction.channel.send(embed=embed, file=file)
            
            # Include PGN
            pgn = game.get_pgn()
            await interaction.channel.send(f"Game PGN:\n```{pgn}```")
            
        except Exception as e:
            logger.error(f"Error resigning game: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send(f"An error occurred: {format_exception(e)}")
            else:
                await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    @chess_group.command(name="pgn")
    async def chess_pgn(interaction: discord.Interaction):
        """Show the PGN of the current game"""
        try:
            # Find the current game in this channel
            game = game_manager.get_game_by_channel(interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "There is no active chess game in this channel.",
                    ephemeral=True
                )
                return
            
            # Get the PGN
            pgn = game.get_pgn()
            
            # Send the PGN
            await interaction.response.send_message(f"Game PGN:\n```{pgn}```")
            
        except Exception as e:
            logger.error(f"Error showing PGN: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    @chess_group.command(name="suggest")
    async def chess_suggest(interaction: discord.Interaction):
        """Suggest moves for the current position"""
        try:
            # Find the current game in this channel
            game = game_manager.get_game_by_channel(interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "There is no active chess game in this channel.",
                    ephemeral=True
                )
                return
            
            # Check if it's the player's turn
            if not game.is_player_turn(interaction.user.id):
                await interaction.response.send_message(
                    "It's not your turn. You can only get suggestions on your turn.",
                    ephemeral=True
                )
                return
            
            # Acknowledge the command
            await interaction.response.defer()
            
            # Get move suggestions
            suggestions = game.get_move_suggestions(count=3)
            
            if not suggestions:
                await interaction.followup.send("No move suggestions available.")
                return
            
            # Format suggestions
            suggestions_text = "Suggested moves:\n"
            for i, (move, eval_score) in enumerate(suggestions):
                suggestions_text += f"{i+1}. **{move}** (Evaluation: {eval_score:.2f})\n"
            
            await interaction.followup.send(suggestions_text)
            
        except Exception as e:
            logger.error(f"Error suggesting move: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send(f"An error occurred: {format_exception(e)}")
            else:
                await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    @chess_group.command(name="analyze")
    async def chess_analyze(interaction: discord.Interaction):
        """Analyze the current position"""
        try:
            # Find the current game in this channel
            game = game_manager.get_game_by_channel(interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "There is no active chess game in this channel.",
                    ephemeral=True
                )
                return
            
            # Acknowledge the command
            await interaction.response.defer()
            
            # Get move suggestions for analysis
            suggestions = game.get_move_suggestions(count=3)
            
            # Create analysis embed
            analysis_embed = await embed_renderer.render_analysis_embed(game, suggestions)
            
            # Send the analysis
            await interaction.followup.send(embed=analysis_embed)
            
        except Exception as e:
            logger.error(f"Error analyzing position: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send(f"An error occurred: {format_exception(e)}")
            else:
                await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    @chess_group.command(name="explain")
    async def chess_explain(interaction: discord.Interaction):
        """Explain the current position"""
        try:
            # Find the current game in this channel
            game = game_manager.get_game_by_channel(interaction.channel_id)
            
            if not game:
                await interaction.response.send_message(
                    "There is no active chess game in this channel.",
                    ephemeral=True
                )
                return
            
            # Acknowledge the command
            await interaction.response.defer()
            
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
            await interaction.followup.send("**Position Analysis**\n\n" + "\n".join(explanation))
            
        except Exception as e:
            logger.error(f"Error explaining position: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send(f"An error occurred: {format_exception(e)}")
            else:
                await interaction.response.send_message(f"An error occurred: {format_exception(e)}", ephemeral=True)
    
    # Add the chess command group to the bot
    bot.tree.add_command(chess_group)
