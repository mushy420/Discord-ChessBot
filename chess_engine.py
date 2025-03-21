
import chess
import chess.pgn
import random
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Set, Union
from utils import logger

class ChessAI:
    """Simple chess AI for move suggestions and evaluations"""
    
    def __init__(self, difficulty: int = 5):
        """Initialize AI with difficulty level (1-10)"""
        self.difficulty = max(1, min(10, difficulty))
        logger.info(f"Chess AI initialized with difficulty {self.difficulty}")
        
        # Piece values for basic evaluation
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        
        # Position value tables for more sophisticated evaluation
        self.pawn_table = [
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5,  5, 10, 25, 25, 10,  5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5, -5,-10,  0,  0,-10, -5,  5,
            5, 10, 10,-20,-20, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        
        # Other piece position tables would be defined here
        # Simplified for brevity
    
    def evaluate_board(self, board: chess.Board) -> float:
        """Evaluate the current board position from white's perspective"""
        if board.is_checkmate():
            # If checkmate, return a high value (positive if opponent is checkmated)
            return -10000 if board.turn else 10000
            
        if board.is_stalemate() or board.is_insufficient_material():
            return 0  # Draw
        
        # Basic material count
        eval_score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = self.piece_values[piece.piece_type]
                
                # Add position value based on piece position tables
                if piece.piece_type == chess.PAWN:
                    sq_idx = square if piece.color else 63 - square
                    value += self.pawn_table[sq_idx]
                
                # Other piece-specific position values would be applied here
                
                eval_score += value if piece.color else -value
        
        # Mobility (number of legal moves)
        mobility = len(list(board.legal_moves))
        eval_score += mobility * 0.1 if board.turn else -mobility * 0.1
        
        # Simple king safety
        king_square = board.king(chess.WHITE)
        if king_square:
            if len(list(board.attackers(chess.BLACK, king_square))) > 0:
                eval_score -= 50
        
        king_square = board.king(chess.BLACK)
        if king_square:
            if len(list(board.attackers(chess.WHITE, king_square))) > 0:
                eval_score += 50
        
        return eval_score

    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Find a good move based on AI difficulty level"""
        if board.is_game_over():
            return None
            
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
            
        # At lower difficulties, occasionally make random moves
        if random.random() < (1.0 - self.difficulty / 10):
            return random.choice(legal_moves)
        
        # Simple minimax with limited depth based on difficulty
        depth = max(1, min(3, self.difficulty // 3))
        best_move = None
        best_score = float('-inf') if board.turn else float('inf')
        
        for move in legal_moves:
            board.push(move)
            score = self._minimax(board, depth - 1, float('-inf'), float('inf'), not board.turn)
            board.pop()
            
            if board.turn and score > best_score:
                best_score = score
                best_move = move
            elif not board.turn and score < best_score:
                best_score = score
                best_move = move
        
        return best_move or random.choice(legal_moves)  # Fallback to random if needed

    def _minimax(self, board: chess.Board, depth: int, alpha: float, beta: float, is_maximizing: bool) -> float:
        """Minimax algorithm with alpha-beta pruning"""
        if depth == 0 or board.is_game_over():
            return self.evaluate_board(board)
        
        if is_maximizing:
            max_eval = float('-inf')
            for move in board.legal_moves:
                board.push(move)
                eval_score = self._minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in board.legal_moves:
                board.push(move)
                eval_score = self._minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval

class ChessGame:
    """Represents a chess game between two players"""
    
    def __init__(self, white_id: int, black_id: int, channel_id: int):
        """Initialize a new chess game"""
        self.board = chess.Board()
        self.white_id = white_id
        self.black_id = black_id
        self.channel_id = channel_id
        self.game_id = f"{white_id}_{black_id}_{int(time.time())}"
        self.move_history = []
        self.created_at = time.time()
        self.last_move_time = time.time()
        self.last_message_id = None
        self.status = "active"  # active, finished
        self.result = None  # white_win, black_win, draw
        self.ai = ChessAI()
        
        logger.info(f"New game created: {self.game_id} between {white_id} (White) and {black_id} (Black)")
    
    @property
    def current_player_id(self) -> int:
        """Get the ID of the player whose turn it is"""
        return self.white_id if self.board.turn else self.black_id
    
    def get_pgn(self) -> str:
        """Get the game in PGN format"""
        game = chess.pgn.Game()
        game.headers["Event"] = "Discord Chess Game"
        game.headers["White"] = f"Player {self.white_id}"
        game.headers["Black"] = f"Player {self.black_id}"
        game.headers["Date"] = time.strftime("%Y.%m.%d")
        
        # Add moves
        node = game
        for move in self.move_history:
            node = node.add_variation(chess.Move.from_uci(move))
            
        return str(game)
    
    def is_player_turn(self, user_id: int) -> bool:
        """Check if it's the specified player's turn"""
        return user_id == self.current_player_id
    
    def make_move(self, move_str: str) -> Tuple[bool, str]:
        """Make a move on the board"""
        try:
            # Try to parse the move (algebraic notation like "e4" or UCI like "e2e4")
            move = None
            
            # Try UCI notation first (e2e4)
            try:
                move = chess.Move.from_uci(move_str)
                if move not in self.board.legal_moves:
                    move = None
            except ValueError:
                pass
                
            # If UCI failed, try SAN notation (e4, Nf3, etc.)
            if not move:
                try:
                    move = self.board.parse_san(move_str)
                except ValueError:
                    pass
            
            # If both failed, check if it's a castling move
            if not move and move_str.lower() in ["o-o", "0-0"]:
                # Kingside castling
                if self.board.turn:  # White
                    move = chess.Move.from_uci("e1g1")
                else:  # Black
                    move = chess.Move.from_uci("e8g8")
                    
            if not move and move_str.lower() in ["o-o-o", "0-0-0"]:
                # Queenside castling
                if self.board.turn:  # White
                    move = chess.Move.from_uci("e1c1")
                else:  # Black
                    move = chess.Move.from_uci("e8c8")
            
            if not move or move not in self.board.legal_moves:
                return False, "Invalid move. Please use algebraic notation (e.g., 'e4', 'Nf3') or UCI notation (e.g., 'e2e4')."
            
            # Make the move
            self.board.push(move)
            self.move_history.append(move.uci())
            self.last_move_time = time.time()
            
            # Check game status
            status_msg = ""
            if self.board.is_checkmate():
                self.status = "finished"
                self.result = "white_win" if not self.board.turn else "black_win"
                winner = "White" if not self.board.turn else "Black"
                status_msg = f"Checkmate! {winner} wins the game."
            elif self.board.is_stalemate():
                self.status = "finished"
                self.result = "draw"
                status_msg = "Stalemate! The game ends in a draw."
            elif self.board.is_insufficient_material():
                self.status = "finished"
                self.result = "draw"
                status_msg = "Draw due to insufficient material."
            elif self.board.is_check():
                status_msg = "Check!"
            
            return True, status_msg
        except Exception as e:
            logger.error(f"Error making move: {str(e)}")
            return False, f"Error making move: {str(e)}"
    
    def get_game_state(self) -> Dict:
        """Get the current game state"""
        return {
            "game_id": self.game_id,
            "fen": self.board.fen(),
            "white_id": self.white_id,
            "black_id": self.black_id,
            "channel_id": self.channel_id,
            "move_history": self.move_history,
            "created_at": self.created_at,
            "last_move_time": self.last_move_time,
            "status": self.status,
            "result": self.result,
            "current_turn": "white" if self.board.turn else "black",
            "is_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_stalemate": self.board.is_stalemate(),
            "is_insufficient_material": self.board.is_insufficient_material()
        }
    
    def get_move_suggestions(self, count: int = 3) -> List[Tuple[str, float]]:
        """Get top move suggestions from the AI"""
        if self.board.is_game_over():
            return []
        
        suggestions = []
        legal_moves = list(self.board.legal_moves)
        
        # Evaluate each move
        for move in legal_moves[:min(10, len(legal_moves))]:  # Limit to 10 candidates for performance
            self.board.push(move)
            evaluation = self.ai.evaluate_board(self.board)
            self.board.pop()
            
            san_move = self.board.san(move)
            suggestions.append((san_move, evaluation))
        
        # Sort by evaluation (highest first for white, lowest first for black)
        if self.board.turn:  # White's turn
            suggestions.sort(key=lambda x: x[1], reverse=True)
        else:  # Black's turn
            suggestions.sort(key=lambda x: x[1])
        
        return suggestions[:count]
    
    def get_ai_move(self) -> Optional[str]:
        """Get a move from the AI"""
        move = self.ai.get_best_move(self.board)
        return self.board.san(move) if move else None

class GameManager:
    """Manages all active chess games"""
    
    def __init__(self):
        """Initialize the game manager"""
        self.active_games = {}  # channel_id -> game
        self.player_games = {}  # player_id -> set of game_ids
        logger.info("Game manager initialized")
    
    def create_game(self, white_id: int, black_id: int, channel_id: int) -> ChessGame:
        """Create a new game between two players"""
        # Check if players are already in a game in this channel
        for game in self.active_games.values():
            if (game.channel_id == channel_id and 
                (white_id in [game.white_id, game.black_id] or 
                 black_id in [game.white_id, game.black_id]) and
                game.status == "active"):
                
                # One of these players is already in a game in this channel
                raise ValueError(f"One of the players is already in an active game in this channel")
        
        # Create new game
        game = ChessGame(white_id, black_id, channel_id)
        
        # Register game
        self.active_games[game.game_id] = game
        
        # Register players
        if white_id not in self.player_games:
            self.player_games[white_id] = set()
        self.player_games[white_id].add(game.game_id)
        
        if black_id not in self.player_games:
            self.player_games[black_id] = set()
        self.player_games[black_id].add(game.game_id)
        
        return game
    
    def get_game(self, game_id: str) -> Optional[ChessGame]:
        """Get a game by ID"""
        return self.active_games.get(game_id)
    
    def get_game_by_channel(self, channel_id: int) -> Optional[ChessGame]:
        """Get the latest active game in a channel"""
        matching_games = [
            game for game in self.active_games.values()
            if game.channel_id == channel_id and game.status == "active"
        ]
        
        if not matching_games:
            return None
            
        # Return the most recent game
        return max(matching_games, key=lambda g: g.created_at)
    
    def get_player_game(self, player_id: int, channel_id: int = None) -> Optional[ChessGame]:
        """Get an active game that a player is participating in"""
        if player_id not in self.player_games:
            return None
            
        game_ids = self.player_games[player_id]
        matching_games = []
        
        for game_id in game_ids:
            if game_id in self.active_games:
                game = self.active_games[game_id]
                if game.status == "active":
                    if channel_id is None or game.channel_id == channel_id:
                        matching_games.append(game)
        
        if not matching_games:
            return None
            
        # Return the most recent game
        return max(matching_games, key=lambda g: g.created_at)
    
    def remove_game(self, game_id: str) -> bool:
        """Remove a game from the active games"""
        if game_id not in self.active_games:
            return False
            
        game = self.active_games[game_id]
        
        # Remove from player registrations
        if game.white_id in self.player_games:
            self.player_games[game.white_id].discard(game_id)
        if game.black_id in self.player_games:
            self.player_games[game.black_id].discard(game_id)
            
        # Remove the game
        del self.active_games[game_id]
        
        return True
    
    def resign_game(self, game_id: str, player_id: int) -> bool:
        """Resign a game for a player"""
        game = self.get_game(game_id)
        if not game:
            return False
            
        if player_id not in [game.white_id, game.black_id]:
            return False
            
        game.status = "finished"
        if player_id == game.white_id:
            game.result = "black_win"
        else:
            game.result = "white_win"
            
        return True
    
    def cleanup_stale_games(self, max_inactive_time: int = 3600) -> int:
        """Clean up games that have been inactive for too long"""
        current_time = time.time()
        stale_game_ids = []
        
        for game_id, game in self.active_games.items():
            if game.status == "active" and current_time - game.last_move_time > max_inactive_time:
                # Game has been inactive for too long
                game.status = "finished"
                game.result = "abandoned"
                stale_game_ids.append(game_id)
        
        # Remove stale games
        for game_id in stale_game_ids:
            self.remove_game(game_id)
            
        return len(stale_game_ids)
    
    def get_statistics(self) -> Dict:
        """Get statistics about games"""
        total_games = len(self.active_games)
        active_games = sum(1 for game in self.active_games.values() if game.status == "active")
        finished_games = total_games - active_games
        
        return {
            "total_games": total_games,
            "active_games": active_games,
            "finished_games": finished_games
        }
