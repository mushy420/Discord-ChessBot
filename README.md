
# ChessBot - Discord Chess Bot

A Discord bot that allows users to play chess against each other directly in Discord channels.

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a Discord bot at the [Discord Developer Portal](https://discord.com/developers/applications)
4. Enable the necessary intents (Message Content, Server Members)
5. Add the bot to your server with the `applications.commands` scope (for slash commands)
6. Copy your bot token from the Discord Developer Portal
7. Configure the `.env` file:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   LOG_LEVEL=INFO
   AI_DIFFICULTY=5
   ```
8. Run the bot:
   ```
   python main.py
   ```
9. After the bot is running, use the `!sync` command to sync slash commands to your server:
   ```
   !sync
   ```
   Or sync globally (takes up to an hour to propagate):
   ```
   !sync global
   ```

## Commands

All commands use the `/chess` prefix (slash command group).

| Command | Description | Usage |
|---------|-------------|-------|
| `/chess help` | Display help information | `/chess help` |
| `/chess challenge @username` | Challenge another user to a game | `/chess challenge @username` |
| `/chess move e4` | Make a move in the current game | `/chess move e4` or `/chess move e2e4` |
| `/chess board` | Display the current board state | `/chess board` |
| `/chess resign` | Resign from the current game | `/chess resign` |
| `/chess pgn` | Show the PGN of the current game | `/chess pgn` |
| `/chess suggest` | Get AI move suggestions | `/chess suggest` |
| `/chess analyze` | Analyze the current position | `/chess analyze` |
| `/chess explain` | Get a simple explanation of the current position | `/chess explain` |

### Management Commands

These commands are only available to the bot owner:

| Command | Description | Usage |
|---------|-------------|-------|
| `!sync` | Sync slash commands to the current guild | `!sync` |
| `!sync global` | Sync slash commands globally | `!sync global` |
| `!status` | Check the bot's status | `!status` |

## Game Features

- Visual chess board representation in Discord
- Challenge system with accept/decline buttons
- Support for algebraic notation (both `e4` and `e2e4` formats)
- Multiple simultaneous games in different channels
- Game state persistence between bot restarts
- Move validation and automatic check/checkmate detection
- Position analysis and move suggestions

## Configuration

You can adjust the following settings in the `.env` file:
- `DISCORD_TOKEN`: Your Discord bot token
- `LOG_LEVEL`: Logging detail level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `AI_DIFFICULTY`: AI difficulty level for move suggestions (1-10)

## Technical Notes

- Games are saved in a `games.json` file that's created automatically
- Logs are written to `chessbot.log` for troubleshooting
- The bot supports multiple games across different channels
- Uses Discord's slash command system for better user experience
- Command registration is done manually via the `!sync` command

  Copyright 2025 CoinKing
