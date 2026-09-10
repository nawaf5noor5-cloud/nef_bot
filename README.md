# EO Smart Signal Telegram Bot

Telegram signal bot for ExpertOption. It discovers active assets/timeframes from the ExpertOption connection, lets the user choose the market and expiry, then calculates a directional signal (CALL/PUT/NO TRADE) from recent candles.

## Design
- Telegram interface
- Market list from ExpertOption active assets
- Timeframe/expiry validation
- Multi-factor analysis: EMA trend, RSI, MACD, momentum, candle structure and ATR/volatility filter
- Confidence score
- NO TRADE when filters disagree or data quality is weak
- No martingale
- Signal-only by default; this build does NOT place real orders automatically

> This is a technical signal engine, not a profit guarantee or financial advice. Binary/options trading can result in rapid loss of capital.

## Setup
1. Create a bot with @BotFather and copy its token.
2. Create a Python 3.10+ virtual environment.
3. Install:
   pip install -r requirements.txt
   python -m playwright install chromium
4. Run `python login.py` to create an ExpertOption session token, following the repository's login approach.
5. Put the token in `.env`.
6. Run `python bot.py`.

## Telegram commands
/start
/markets
/timeframes
/setmarket EURUSD
/settime 60
/analyze
/settings
/reset

The bot only offers assets/timeframes reported as active by the ExpertOption API. It will refuse an unavailable selection.

## Token security
Never send Telegram or ExpertOption tokens to anyone. Keep `.env` private.
