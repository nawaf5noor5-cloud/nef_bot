import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("EO_AUTH_TOKEN", "")
DEMO = os.getenv("EO_DEMO", "true").lower() == "true"
LOOKBACK = int(os.getenv("CANDLE_LOOKBACK", "120"))
MIN_CONF = float(os.getenv("MIN_CONFIDENCE", "72"))

class SignalEngine:
    def __init__(self):
        self.client = None
        self.market = None
        self.duration = None
        self._connected = False

    async def connect(self):
        if self._connected:
            return
        if not TOKEN:
            raise RuntimeError("EO_AUTH_TOKEN is missing")
        self.client = ExpertOptionAsync(TOKEN, demo=DEMO, url=DEFAULT_SERVER)
        await self.client.connect()
        self._connected = True

    async def active_markets(self):
        await self.connect()
        # The library exposes active-asset helpers. Fall back to fetched assets
        # if the installed revision uses a different method.
        try:
            assets = await self.client.get_assets()
        except Exception:
            assets = getattr(self.client, "assets", [])
        names = []
        for a in assets or []:
            if isinstance(a, dict):
                active = a.get("is_active", a.get("active", True))
                symbol = a.get("symbol") or a.get("name")
                if active and symbol:
                    names.append(str(symbol).upper())
            else:
                names.append(str(a))
        return sorted(set(names))

    async def available_timeframes(self):
        # ExpertOption's candle period support can vary by account/asset.
        # Probe common supported periods through the active connection.
        await self.connect()
        common = [5, 10, 15, 30, 60, 120, 180, 300, 600, 900]
        supported = []
        asset_id = get_asset_id(self.market) if self.market else None
        if not asset_id:
            # Without a market selected, expose the common set; settime then validates.
            return common
        for p in common:
            try:
                df = await self.client.get_candles(
                    asset_id=asset_id, period=p, offset=0, duration=max(300, p*LOOKBACK)
                )
                if df is not None and len(df) >= 30:
                    supported.append(p)
            except Exception:
                pass
        return supported

    async def validate_market(self, symbol):
        return bool(get_asset_id(symbol))

    async def validate_timeframe(self, seconds):
        return seconds in await self.available_timeframes()

    async def candles(self, symbol, period):
        await self.connect()
        asset_id = get_asset_id(symbol)
        if not asset_id:
            raise ValueError("Unknown asset")
        df = await self.client.get_candles(
            asset_id=asset_id,
            period=period,
            offset=0,
            duration=max(period * LOOKBACK, 600)
        )
        if df is None or len(df) < 60:
            raise ValueError("Insufficient candle data")
        df = pd.DataFrame(df).copy()
        # Normalize common column names.
        rename = {}
        for c in df.columns:
            lc = str(c).lower()
            if lc in ("open", "o"): rename[c] = "open"
            elif lc in ("high", "h"): rename[c] = "high"
            elif lc in ("low", "l"): rename[c] = "low"
            elif lc in ("close", "c"): rename[c] = "close"
        df = df.rename(columns=rename)
        needed = ["open","high","low","close"]
        if not all(x in df.columns for x in needed):
            raise ValueError(f"Unexpected candle columns: {list(df.columns)}")
        return df[needed].astype(float).dropna()

    def indicators(self, df):
        x = df.copy()
        x["ema9"] = x.close.ewm(span=9, adjust=False).mean()
        x["ema21"] = x.close.ewm(span=21, adjust=False).mean()
        x["ema50"] = x.close.ewm(span=50, adjust=False).mean()

        delta = x.close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        x["rsi"] = 100 - (100 / (1 + rs))

        fast = x.close.ewm(span=12, adjust=False).mean()
        slow = x.close.ewm(span=26, adjust=False).mean()
        x["macd"] = fast - slow
        x["macd_signal"] = x.macd.ewm(span=9, adjust=False).mean()

        tr = pd.concat([
            x.high-x.low,
            (x.high-x.close.shift()).abs(),
            (x.low-x.close.shift()).abs()
        ], axis=1).max(axis=1)
        x["atr"] = tr.rolling(14).mean()
        x["body"] = (x.close-x.open).abs()
        x["range"] = x.high-x.low
        return x.dropna()

    def score(self, x):
        r = x.iloc[-1]
        p = x.iloc[-2]
        call = put = 0
        reasons_call, reasons_put = [], []

        if r.ema9 > r.ema21 > r.ema50:
            call += 2; reasons_call.append("EMA trend bullish")
        elif r.ema9 < r.ema21 < r.ema50:
            put += 2; reasons_put.append("EMA trend bearish")

        if r.rsi >= 52 and r.rsi <= 68:
            call += 1.5; reasons_call.append(f"RSI {r.rsi:.1f}")
        elif r.rsi <= 48 and r.rsi >= 32:
            put += 1.5; reasons_put.append(f"RSI {r.rsi:.1f}")

        if r.macd > r.macd_signal and r.macd > p.macd:
            call += 1.5; reasons_call.append("MACD momentum")
        elif r.macd < r.macd_signal and r.macd < p.macd:
            put += 1.5; reasons_put.append("MACD momentum")

        bullish = r.close > r.open and r.body >= 0.45*r.range
        bearish = r.close < r.open and r.body >= 0.45*r.range
        if bullish:
            call += 1; reasons_call.append("strong bullish candle")
        if bearish:
            put += 1; reasons_put.append("strong bearish candle")

        # Avoid extreme volatility / tiny candles.
        if r.range > 0 and r.atr > 0:
            ratio = r.range / r.atr
            if ratio > 2.5:
                call -= 1; put -= 1
        if r.body / max(r.range, 1e-9) < 0.15:
            call -= .5; put -= .5

        total = max(call, put)
        direction = "CALL" if call > put else "PUT" if put > call else "NO TRADE"
        gap = abs(call-put)
        confidence = min(95, max(0, 50 + gap*10 + max(total-3,0)*5))
        if confidence < MIN_CONF or direction == "NO TRADE":
            direction = "NO TRADE"

        return {
            "direction": direction,
            "confidence": round(confidence,1),
            "rsi": round(float(r.rsi),1),
            "call_score": round(call,2),
            "put_score": round(put,2),
            "call_reasons": reasons_call,
            "put_reasons": reasons_put,
            "close": float(r.close),
            "atr": float(r.atr)
        }

    async def analyze(self, symbol, duration):
        df = await self.candles(symbol, duration)
        x = self.indicators(df)
        if len(x) < 20:
            raise ValueError("Not enough clean indicators")
        result = self.score(x)
        result.update({"symbol": symbol, "duration": duration, "candles": len(x)})
        return result

    def format_result(self, r):
        d = r["direction"]
        emoji = "🟢" if d == "CALL" else "🔴" if d == "PUT" else "⚪"
        reasons = r["call_reasons"] if d == "CALL" else r["put_reasons"]
        reason_text = "\n".join(f"• {x}" for x in reasons) or "• تضارب/ضعف الإشارات"
        return (
            f"{emoji} SIGNAL: {d}\n\n"
            f"📊 Market: {r['symbol']}\n"
            f"⏱ Expiry/TF: {r['duration']}s\n"
            f"🎯 Confidence: {r['confidence']}%\n"
            f"RSI: {r['rsi']}\n"
            f"CALL score: {r['call_score']}\n"
            f"PUT score: {r['put_score']}\n\n"
            f"الأسباب:\n{reason_text}\n\n"
            "⚠️ ليست ضمانًا للربح. إذا ظهرت NO TRADE فلا تدخل الصفقة."
        )
