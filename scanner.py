import yfinance as yf
import pandas as pd
import numpy as np


# ==============================
# NSE STOCK LIST
# ==============================

stocks = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "ITC.NS",
    "SBIN.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "TRENT.NS",
    "IRFC.NS",
    "IRCTC.NS",
    "SUZLON.NS",
    "JIOFIN.NS",
    "IREDA.NS"
]


# ==============================
# RSI
# ==============================

def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# ==============================
# MACD
# ==============================

def calculate_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    return macd, signal


# ==============================
# ADX
# ==============================

def calculate_adx(data, period=14):

    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    plus_dm = high.diff()
    minus_dm = low.diff()

    plus_dm = plus_dm.where(
        (plus_dm > minus_dm) & (plus_dm > 0), 0
    )

    minus_dm = minus_dm.where(
        (minus_dm > plus_dm) & (minus_dm > 0), 0
    )

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = 100 * plus_dm.rolling(period).mean() / atr
    minus_di = 100 * minus_dm.rolling(period).mean() / atr

    dx = (
        abs(plus_di - minus_di)
        / (plus_di + minus_di)
    ) * 100

    adx = dx.rolling(period).mean()

    return adx


# ==============================
# STOCK SCANNER
# ==============================

results = []


for symbol in stocks:

    try:

        print("Scanning:", symbol)

        data = yf.download(
            symbol,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if data.empty:
            continue

        data = data.dropna()

        close = data["Close"]

        # DMA
        data["DMA20"] = close.rolling(20).mean()
        data["DMA50"] = close.rolling(50).mean()
        data["DMA200"] = close.rolling(200).mean()

        # RSI
        data["RSI"] = calculate_rsi(close)

        # MACD
        data["MACD"], data["MACD_SIGNAL"] = calculate_macd(close)

        # ADX
        data["ADX"] = calculate_adx(data)

        # Volume average
        data["AVG_VOLUME_20"] = data["Volume"].rolling(20).mean()

        # Volume breakout
        data["VOLUME_BREAKOUT"] = (
            data["Volume"] > data["AVG_VOLUME_20"] * 1.5
        )

        last = data.iloc[-1]

        price = float(last["Close"])
        dma20 = float(last["DMA20"])
        dma50 = float(last["DMA50"])
        dma200 = float(last["DMA200"])
        rsi = float(last["RSI"])
        macd = float(last["MACD"])
        macd_signal = float(last["MACD_SIGNAL"])
        adx = float(last["ADX"])

        volume_breakout = bool(last["VOLUME_BREAKOUT"])

        # ==============================
        # BUY CONDITIONS
        # ==============================

        buy_signal = (
            price > dma20
            and price > dma50
            and price > dma200
            and rsi > 50
            and macd > macd_signal
            and adx > 20
            and volume_breakout
        )

        results.append({
            "Stock": symbol.replace(".NS", ""),
            "Price": round(price, 2),
            "DMA20": round(dma20, 2),
            "DMA50": round(dma50, 2),
            "DMA200": round(dma200, 2),
            "RSI": round(rsi, 2),
            "MACD": round(macd, 2),
            "MACD Signal": round(macd_signal, 2),
            "ADX": round(adx, 2),
            "Volume Breakout": volume_breakout,
            "BUY Signal": "BUY" if buy_signal else ""
        })

    except Exception as e:

        print("Error:", symbol, e)


# ==============================
# RESULT
# ==============================

result_df = pd.DataFrame(results)

print("\n==============================")
print("STOCK SCANNER RESULT")
print("==============================")

print(result_df.to_string(index=False))
