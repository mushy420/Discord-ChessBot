481
482
483
484
485
486
487
488
489
490
491
492
493
494
495
496
497
498
499
500
501
502
503
504
505
506
507
508
509
510
511
512
513
514
515
516
517
518
519
520
521
522
523
524
525
526
527
528
529
530
531
532
533
534
535
536
537
538
539
540
541
542
543
544
545
546
547
548
549
550
551
552
553
554
555
556
557
558
559
560
⌄
⌄

import discord
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

async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(ChessCommands(bot))
