import yfinance as yf
import pandas as pd
import numpy as np
import gspread
import os
import json
from google.oauth2.service_account import Credentials


# ==============================
# GOOGLE SHEETS SETTINGS
# ==============================

SPREADSHEET_ID = "1Pyo8Lhivc-Kud3Xt7bnObUedV6DLiHpeRnJVkQe8Ivs"
WORKSHEET_NAME = "NIFTY 500 SWING"


# ==============================
# GOOGLE SHEETS CONNECTION
# ==============================

creds_json = os.environ.get("GCP_CREDENTIALS")

if not creds_json:
    raise Exception("GCP_CREDENTIALS secret not found")

service_account_info = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=scopes
)

gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(SPREADSHEET_ID)

worksheet = spreadsheet.worksheet(WORKSHEET_NAME)


# ==============================
# NSE STOCK LIST
# ==============================

# ==============================
# LOAD STOCK LIST
# ==============================

with open("nifty500.txt", "r") as f:
    stocks = [line.strip() for line in f.readlines() if line.strip()]
print("Total Stocks:", len(stocks))
for symbol in stocks:
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

    # yfinance multi-column data को Series में बदलना
    if isinstance(high, pd.DataFrame):
        high = high.iloc[:, 0]

    if isinstance(low, pd.DataFrame):
        low = low.iloc[:, 0]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

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

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = (
        100 *
        plus_dm.rolling(period).mean()
        / atr
    )

    minus_di = (
        100 *
        minus_dm.rolling(period).mean()
        / atr
    )

    denominator = plus_di + minus_di

    dx = (
        abs(plus_di - minus_di)
        / denominator.replace(0, np.nan)
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

        # yfinance MultiIndex columns ko normal columns mein convert karo
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

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

        # Volume
        data["AVG_VOLUME_20"] = (
            data["Volume"].rolling(20).mean()
        )

        data["VOLUME_BREAKOUT"] = (
            data["Volume"]
            > data["AVG_VOLUME_20"] * 1.5
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

        volume_breakout = bool(
            last["VOLUME_BREAKOUT"]
        )

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
            "Volume Breakout": "YES" if volume_breakout else "NO",
            "BUY Signal": "BUY" if buy_signal else ""
        })

    except Exception as e:

        print("Error:", symbol, e)


# ==============================
# DATAFRAME
# ==============================

result_df = pd.DataFrame(results)


# ==============================
# UPLOAD TO GOOGLE SHEETS
# ==============================

print("\nUploading results to Google Sheets...")


if not result_df.empty:

    worksheet.clear()

    worksheet.update(
        [result_df.columns.values.tolist()]
        + result_df.values.tolist()
    )

    print("Google Sheet updated successfully!")

else:

    print("No scanner results found.")


# ==============================
# DISPLAY RESULT
# ==============================

print("\n==============================")
print("STOCK SCANNER RESULT")
print("==============================")

print(result_df.to_string(index=False))
