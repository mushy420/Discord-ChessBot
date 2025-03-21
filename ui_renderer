
import chess
import io
from PIL import Image, ImageDraw, ImageFont
import os
from typing import Tuple, Optional, Dict, List
import asyncio
import discord
from utils import logger

class BoardRenderer:
    """Chess board renderer that creates images for Discord messages"""
    
    def __init__(self):
        """Initialize renderer with board configuration"""
        self.board_size = 480  # Size of the board in pixels
        self.square_size = self.board_size // 8
        
        # Colors for the board
        self.light_square_color = (240, 237, 235)
        self.dark_square_color = (181, 184, 177)
        self.highlight_color = (247, 202, 51, 160)  # Semi-transparent yellow
        self.last_move_color = (42, 150, 234, 180)  # Semi-transparent blue
        self.check_color = (235, 97, 80, 180)  # Semi-transparent red
        
        # Load piece images
        self.piece_images = {}
        self._load_piece_images()
        
        # Coordinates for board notation
        self.show_coordinates = True
        self.coordinate_color = (60, 60, 60)
        self.coordinate_font_size = 14
        
        try:
            # Try to load font (with fallbacks)
            font_candidates = [
                "SFCompact-Regular.ttf",  # Apple font
                "Arial.ttf",
                "DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "Roboto-Regular.ttf",
                "/System/Library/Fonts/SFCompact-Regular.otf",
                "/Library/Fonts/Arial.ttf"
            ]
            
            self.font = None
            for font_path in font_candidates:
                try:
                    if os.path.exists(font_path):
                        self.font = ImageFont.truetype(font_path, self.coordinate_font_size)
                        logger.info(f"Using font: {font_path}")
                        break
                except Exception:
                    continue
                    
            if not self.font:
                # Use default font if none of the above work
                self.font = ImageFont.load_default()
                logger.warning("Using default font as no system fonts were found")
                
        except Exception as e:
            logger.error(f"Error loading font: {str(e)}")
            self.font = ImageFont.load_default()
    
    def _load_piece_images(self):
        """Load piece images or create default representations"""
        try:
            # This would ideally load actual piece images
            # For now, we'll generate simple piece representations
            
            # Define piece symbols for fallback
            piece_symbols = {
                'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
                'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
            }
            
            # Create simple piece images with text
            for piece_symbol, unicode_symbol in piece_symbols.items():
                # Create a transparent image
                img = Image.new('RGBA', (self.square_size, self.square_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Determine color
                color = (40, 40, 40) if piece_symbol.isupper() else (80, 80, 80)
                
                # Draw piece symbol
                font_size = int(self.square_size * 0.75)
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                except Exception:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()
                
                # Center the symbol in the square
                try:
                    # For newer Pillow versions
                    _, _, width, height = draw.textbbox((0, 0), unicode_symbol, font=font)
                except AttributeError:
                    # For older Pillow versions
                    width, height = draw.textsize(unicode_symbol, font=font)
                
                position = ((self.square_size - width) // 2, (self.square_size - height) // 2 - 5)
                
                # Draw the piece with a slight shadow for better visibility
                shadow_offset = 2
                draw.text((position[0] + shadow_offset, position[1] + shadow_offset), 
                           unicode_symbol, fill=(0, 0, 0, 100), font=font)
                draw.text(position, unicode_symbol, fill=color, font=font)
                
                self.piece_images[piece_symbol] = img
                
            logger.info("Generated piece images")
            
        except Exception as e:
            logger.error(f"Error loading piece images: {str(e)}")
    
    def _get_square_color(self, rank: int, file: int) -> Tuple[int, int, int]:
        """Get the color for a square at the given rank and file"""
        is_light_square = (rank + file) % 2 == 0
        return self.light_square_color if is_light_square else self.dark_square_color
    
    def render_board(self, board: chess.Board, last_move: Optional[chess.Move] = None) -> Image.Image:
        """Render the chess board as an image"""
        # Create a new image for the board
        img = Image.new('RGB', (self.board_size, self.board_size), (240, 240, 240))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Draw each square
        for rank in range(8):
            for file in range(8):
                square_color = self._get_square_color(rank, file)
                
                # Calculate pixel coordinates
                x0, y0 = file * self.square_size, (7 - rank) * self.square_size
                x1, y1 = x0 + self.square_size, y0 + self.square_size
                
                # Draw square
                draw.rectangle([(x0, y0), (x1, y1)], fill=square_color)
                
                # Add coordinates if needed
                if self.show_coordinates:
                    if rank == 0:  # Bottom rank, show file letters
                        file_letter = chr(97 + file)  # 'a' through 'h'
                        draw.text((x0 + self.square_size - 12, y1 - 14), 
                                  file_letter, fill=self.coordinate_color, font=self.font)
                    
                    if file == 0:  # Leftmost file, show rank numbers
                        rank_number = str(rank + 1)
                        draw.text((x0 + 4, y0 + 2), 
                                  rank_number, fill=self.coordinate_color, font=self.font)
        
        # Highlight last move
        if last_move:
            from_square = last_move.from_square
            to_square = last_move.to_square
            
            for square in [from_square, to_square]:
                file, rank = chess.square_file(square), chess.square_rank(square)
                x, y = file * self.square_size, (7 - rank) * self.square_size
                draw.rectangle([(x, y), (x + self.square_size, y + self.square_size)], 
                              fill=self.last_move_color)
        
        # Highlight king if in check
        if board.is_check():
            king_square = board.king(board.turn)
            if king_square is not None:
                file, rank = chess.square_file(king_square), chess.square_rank(king_square)
                x, y = file * self.square_size, (7 - rank) * self.square_size
                draw.rectangle([(x, y), (x + self.square_size, y + self.square_size)], 
                              fill=self.check_color)
        
        # Draw pieces on the board
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                
                if piece:
                    piece_symbol = piece.symbol()
                    piece_img = self.piece_images.get(piece_symbol)
                    
                    if piece_img:
                        x, y = file * self.square_size, (7 - rank) * self.square_size
                        img.paste(piece_img, (x, y), piece_img)
        
        # Apply subtle border and shadow
        final_img = Image.new('RGB', (self.board_size + 12, self.board_size + 12), (240, 240, 240))
        # Draw a shadow
        shadow = Image.new('RGBA', (self.board_size + 2, self.board_size + 2), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([(0, 0), (self.board_size + 1, self.board_size + 1)], outline=(80, 80, 80, 160), width=1)
        final_img.paste(shadow, (6, 6), shadow)
        
        # Draw a border
        border = Image.new('RGBA', (self.board_size + 2, self.board_size + 2), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.rectangle([(0, 0), (self.board_size + 1, self.board_size + 1)], outline=(60, 60, 60), width=1)
        final_img.paste(border, (5, 5), border)
        
        # Paste the board
        final_img.paste(img, (6, 6))
        
        return final_img
    
    def get_board_image(self, board: chess.Board, last_move: Optional[chess.Move] = None) -> io.BytesIO:
        """Get a rendered board image as bytes"""
        img = self.render_board(board, last_move)
        
        # Convert image to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return buffer

class ChessEmbedRenderer:
    """Renders chess game information as Discord embeds"""
    
    def __init__(self):
        """Initialize the embed renderer"""
        self.board_renderer = BoardRenderer()
    
    async def render_game_embed(
        self, 
        game, 
        white_user: Optional[discord.User] = None, 
        black_user: Optional[discord.User] = None,
        bot = None
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        """Render a chess game as a Discord embed with an image"""
        try:
            # Get users if they're not provided
            if bot and not white_user and game.white_id > 0:
                try:
                    white_user = await bot.fetch_user(game.white_id)
                except Exception:
                    white_user = None
                    
            if bot and not black_user and game.black_id > 0:
                try:
                    black_user = await bot.fetch_user(game.black_id)
                except Exception:
                    black_user = None
            
            # Determine player names
            white_name = white_user.display_name if white_user else f"Player {game.white_id}"
            black_name = black_user.display_name if black_user else f"Player {game.black_id}"
            
            # Get last move if any
            last_move = None
            if game.move_history:
                try:
                    last_move = chess.Move.from_uci(game.move_history[-1])
                except Exception:
                    pass
            
            # Get board image
            board_image = self.board_renderer.get_board_image(game.board, last_move)
            board_file = discord.File(board_image, filename="board.png")
            
            # Create embed
            embed = discord.Embed(title="Chess Game", color=0x2f3136)
            
            # Add player information
            embed.add_field(name="White", value=white_name, inline=True)
            embed.add_field(name="Black", value=black_name, inline=True)
            
            # Game status
            status_text = ""
            if game.status == "finished":
                if game.result == "white_win":
                    status_text = f"Game over. {white_name} (White) wins!"
                elif game.result == "black_win":
                    status_text = f"Game over. {black_name} (Black) wins!"
                elif game.result == "draw":
                    status_text = "Game over. It's a draw!"
                else:
                    status_text = "Game over."
            else:
                current_turn = "White" if game.board.turn else "Black"
                current_player = white_name if game.board.turn else black_name
                status_text = f"{current_player}'s turn ({current_turn})"
                
                if game.board.is_check():
                    status_text += " - Check!"
            
            embed.description = status_text
            
            # Add move information if available
            if game.move_history:
                # Format last few moves in a readable way
                moves_text = ""
                board = chess.Board()
                
                for i, move_uci in enumerate(game.move_history[-10:]):  # Show up to last 10 moves
                    move = chess.Move.from_uci(move_uci)
                    san = board.san(move)
                    
                    move_num = (i + (len(game.move_history) - len(game.move_history[-10:]))) + 1
                    if move_num % 2 == 1:  # White's move
                        moves_text += f"{(move_num + 1) // 2}. {san} "
                    else:  # Black's move
                        moves_text += f"{san} "
                    
                    board.push(move)
                
                embed.add_field(name="Last Moves", value=f"```{moves_text}```", inline=False)
            
            embed.set_image(url="attachment://board.png")
            embed.set_footer(text=f"Game ID: {game.game_id}")
            
            return embed, board_file
            
        except Exception as e:
            logger.error(f"Error rendering game embed: {str(e)}")
            # Return a simple error embed
            embed = discord.Embed(
                title="Chess Game", 
                description=f"Error rendering game: {str(e)}", 
                color=0xff0000
            )
            return embed, None
    
    async def render_challenge_embed(
        self, 
        challenger: discord.User, 
        challenged: discord.User
    ) -> discord.Embed:
        """Render a chess challenge as a Discord embed"""
        embed = discord.Embed(
            title="Chess Challenge", 
            description=f"{challenger.mention} has challenged {challenged.mention} to a game of chess!", 
            color=0x3498db
        )
        
        embed.add_field(name="To Accept", value="React with ✅", inline=True)
        embed.add_field(name="To Decline", value="React with ❌", inline=True)
        
        embed.set_footer(text="This challenge will expire in 5 minutes.")
        
        return embed
    
    async def render_help_embed(self) -> discord.Embed:
        """Render the help information as a Discord embed"""
        embed = discord.Embed(
            title="ChessBot Help", 
            description="Commands and instructions for playing chess", 
            color=0x3498db
        )
        
        # Game commands
        game_commands = (
            "`!chess challenge @user` - Challenge a user to a chess game\n"
            "`!chess move e4` - Make a move using algebraic notation\n"
            "`!chess board` - Display the current board\n"
            "`!chess resign` - Resign the current game\n"
            "`!chess pgn` - Get the PGN of the current game"
        )
        embed.add_field(name="Game Commands", value=game_commands, inline=False)
        
        # Help commands
        help_commands = (
            "`!chess help` - Show this help message\n"
            "`!chess analyze` - Analyze the current position\n"
            "`!chess suggest` - Get move suggestions\n"
            "`!chess explain` - Get an explanation of the current position"
        )
        embed.add_field(name="Help Commands", value=help_commands, inline=False)
        
        # How to make moves
        move_help = (
            "You can make moves using:\n"
            "• Standard Algebraic Notation (e.g., `e4`, `Nf3`, `Qxd5`)\n"
            "• UCI notation (e.g., `e2e4`, `g1f3`)\n"
            "• Castling notation (`0-0` for kingside, `0-0-0` for queenside)"
        )
        embed.add_field(name="Making Moves", value=move_help, inline=False)
        
        embed.set_footer(text="ChessBot | Build 1.0")
        
        return embed

    async def render_analysis_embed(self, game, suggestions: List[Tuple[str, float]]) -> discord.Embed:
        """Render position analysis as a Discord embed"""
        embed = discord.Embed(
            title="Position Analysis", 
            color=0x3498db
        )
        
        # Current position status
        position_status = ""
        if game.board.is_checkmate():
            position_status = "Checkmate!"
        elif game.board.is_stalemate():
            position_status = "Stalemate!"
        elif game.board.is_insufficient_material():
            position_status = "Draw due to insufficient material"
        elif game.board.is_check():
            position_status = "Check!"
        else:
            # Format evaluation
            if suggestions and len(suggestions) > 0:
                best_move, eval_score = suggestions[0]
                
                # Normalize the score for display
                if abs(eval_score) < 0.01:
                    eval_str = "0.00"
                else:
                    eval_str = f"{eval_score:.2f}"
                
                if game.board.turn:  # White to move
                    if eval_score > 5:
                        position_status = f"White is winning (+{eval_str})"
                    elif eval_score > 1.5:
                        position_status = f"White has a strong advantage (+{eval_str})"
                    elif eval_score > 0.5:
                        position_status = f"White has a slight advantage (+{eval_str})"
                    elif eval_score > -0.5:
                        position_status = f"Position is roughly equal ({eval_str})"
                    elif eval_score > -1.5:
                        position_status = f"Black has a slight advantage ({eval_str})"
                    elif eval_score > -5:
                        position_status = f"Black has a strong advantage ({eval_str})"
                    else:
                        position_status = f"Black is winning ({eval_str})"
                else:  # Black to move
                    if eval_score < -5:
                        position_status = f"Black is winning ({eval_str})"
                    elif eval_score < -1.5:
                        position_status = f"Black has a strong advantage ({eval_str})"
                    elif eval_score < -0.5:
                        position_status = f"Black has a slight advantage ({eval_str})"
                    elif eval_score < 0.5:
                        position_status = f"Position is roughly equal ({eval_str})"
                    elif eval_score < 1.5:
                        position_status = f"White has a slight advantage (+{eval_str})"
                    elif eval_score < 5:
                        position_status = f"White has a strong advantage (+{eval_str})"
                    else:
                        position_status = f"White is winning (+{eval_str})"
            else:
                position_status = "Position analysis not available"
        
        embed.description = position_status
        
        # Add suggested moves if available
        if suggestions and len(suggestions) > 0:
            suggestions_text = ""
            for i, (move, eval_score) in enumerate(suggestions):
                suggestions_text += f"{i+1}. **{move}** ({eval_score:.2f})\n"
            
            embed.add_field(name="Suggested Moves", value=suggestions_text, inline=False)
        
        # Add position statistics
        stats = []
        stats.append(f"Material count: White {self._get_material_count(game.board, chess.WHITE)}, Black {self._get_material_count(game.board, chess.BLACK)}")
        stats.append(f"Number of legal moves: {len(list(game.board.legal_moves))}")
        stats.append(f"Castling rights: {'K' if game.board.has_kingside_castling_rights(chess.WHITE) else ''}{'Q' if game.board.has_queenside_castling_rights(chess.WHITE) else ''}{'k' if game.board.has_kingside_castling_rights(chess.BLACK) else ''}{'q' if game.board.has_queenside_castling_rights(chess.BLACK) else ''}")
        
        embed.add_field(name="Position Statistics", value="\n".join(stats), inline=False)
        
        embed.set_footer(text="Analysis powered by ChessBot AI")
        
        return embed
    
    def _get_material_count(self, board: chess.Board, color: chess.Color) -> int:
        """Calculate material count for a side"""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        
        material = sum(
            piece_values[piece.piece_type]
            for piece in board.pieces(color=color)
            if piece.piece_type != chess.KING
        )
        
        return material
