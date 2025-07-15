# -*- coding: utf-8 -*-

# =============================================================================
# --- DISCLAIMER / คำเตือน ---
# =============================================================================
# สคริปต์นี้จัดทำขึ้นเพื่อการศึกษาเท่านั้น และไม่ใช่คำแนะนำทางการเงิน
# การลงทุนในสินทรัพย์ดิจิทัลมีความเสี่ยงสูงมาก ควรศึกษาข้อมูลด้วยตนเอง
# และทดสอบกลยุทธ์ด้วยบัญชีทดลอง (Paper Trading) ก่อนใช้เงินจริง
# =============================================================================

import ccxt.async_support as ccxt  # <-- เปลี่ยนเป็น async_support
import pandas as pd
import pandas_ta as ta
import time
import asyncio
import telegram

# =============================================================================
# --- ⚙️ USER CONFIGURATION / ตั้งค่าโดยผู้ใช้ ---
# =============================================================================

# -- KuCoin API Keys --
# ใส่ Key ของคุณที่นี่ (ควรเก็บไว้ในที่ปลอดภัย)
KUCOIN_API_KEY = '6874f5b86a7e4f00012d055d'
KUCOIN_API_SECRET = 'a75d24cf-2dff-4311-946d-577703ebf896'

# -- Telegram Bot Configuration --
# ใส่ Token และ Chat ID ของคุณที่นี่
TELEGRAM_TOKEN = '7518863293:AAGti1z6f9_vOPVeM3XIWC57cA1wRX5rKqk'
TELEGRAM_CHAT_ID = '6323845930'

# -- Market Configuration --
# รายชื่อเหรียญที่ต้องการวิเคราะห์
SYMBOLS_TO_WATCH = ['BTC/USDT', 'ETH/USDT', 'XLM/USDT', 'CHZ/USDT', 'LUNC/USDT']
TIMEFRAME = '4h'  # ไทม์เฟรมที่ต้องการวิเคราะห์: '1h', '4h', '1d'
LOOP_INTERVAL_MINUTES = 30  # วิเคราะห์ซ้ำทุกๆ กี่นาที

# =============================================================================

async def send_telegram_message(message: str):
    """ฟังก์ชันสำหรับส่งข้อความไปยัง Telegram"""
    if TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN' or TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID':
        print("❗️ คำเตือน: กรุณาตั้งค่า TELEGRAM_TOKEN และ TELEGRAM_CHAT_ID ก่อน")
        return

    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        # ใช้ parse_mode='Markdown' เพื่อให้ข้อความสวยงาม
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')
        print("✅ แจ้งเตือนถูกส่งไปยัง Telegram สำเร็จ!")
    except Exception as e:
        print(f"❌ ไม่สามารถส่งการแจ้งเตือนไปยัง Telegram ได้: {e}")


async def analyze_market(exchange: ccxt.Exchange, symbol: str, timeframe: str, limit: int = 250):
    """ดึงข้อมูลราคาและคำนวณ technical indicators"""
    try:
        print(f"🔄 [{symbol}] กำลังดึงข้อมูล {limit} แท่งเทียนล่าสุด ({timeframe})...")
        # ใช้ await เพราะเป็นการเชื่อมต่อเครือข่าย
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # --- คำนวณ Indicators ---
        df.ta.sma(length=200, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df['volume_sma_50'] = df['volume'].rolling(window=50).mean()

        return df

    except Exception as e:
        print(f"❗️ [{symbol}] เกิดข้อผิดพลาดในการดึงหรือวิเคราะห์ข้อมูล: {e}")
        return None


def get_trading_signal(df: pd.DataFrame):
    """สร้างสัญญาณการซื้อขายจากข้อมูลที่วิเคราะห์อย่างละเอียด"""
    if df is None or df.empty:
        return "ไม่สามารถสร้างสัญญาณได้เนื่องจากไม่มีข้อมูล"

    latest = df.iloc[-1]
    
    # --- ดึงค่าจาก Indicators ---
    price = latest['close']
    sma200 = latest['SMA_200']
    rsi = latest['RSI_14']
    macd = latest['MACD_12_26_9']
    macd_signal = latest['MACDs_12_26_9']
    bb_upper = latest['BBU_20_2.0']
    bb_lower = latest['BBL_20_2.0']
    volume = latest['volume']
    volume_sma = latest['volume_sma_50']
    
    # --- ตรรกะการตัดสินใจ ---
    long_term_trend = "🟢 UPTREND (ถือยาวได้)" if price > sma200 else "🔴 DOWNTREND (เสี่ยงสูง)"
    
    # ตรวจสอบสัญญาณ MACD Crossover
    macd_cross_above = macd > macd_signal and df.iloc[-2]['MACD_12_26_9'] <= df.iloc[-2]['MACDs_12_26_9']
    
    action, reason = "NEUTRAL / HOLD (เป็นกลาง)", "สัญญาณยังไม่ชัดเจน"

    if long_term_trend.startswith("🟢"):
        if macd_cross_above and rsi < 65:
            action, reason = "✅ STRONG BUY (น่าสนใจเข้าซื้อ)", "เกิดสัญญาณซื้อ MACD Crossover ในเทรนด์ขาขึ้น"
        elif price <= bb_lower and rsi < 40:
            action, reason = "📈 BUY THE DIP (พิจารณาซื้อช่วงย่อตัว)", "ราคาลงมาทดสอบขอบล่าง Bollinger Band"
        elif price >= bb_upper and rsi > 70:
            action, reason = "💰 TAKE PROFIT (พิจารณาขายทำกำไร)", "ราคาชนขอบบน Bollinger Band และ RSI Overbought"
        else:
            action, reason = "HOLD LONG-TERM (ถือยาว)", "ภาพรวมยังเป็นขาขึ้น แต่ไม่มีสัญญาณระยะสั้น"
    else: # Downtrend
        if macd > macd_signal:
             action, reason = "CAUTIOUS HOLD (ถือด้วยความระมัดระวัง)", "อาจเป็นการดีดตัวขึ้นระยะสั้นในตลาดขาลง"
        else:
            action, reason = "🚫 AVOID / SELL (หลีกเลี่ยง/ขาย)", "ตลาดยังคงเป็นขาลงอย่างชัดเจน"

    # --- สร้างข้อความแจ้งเตือน ---
    alert_message = f"""
*🔔 CRYPTO ALERT: {df.name}*
--------------------------------------
*ราคา:* `{price:,.4f} USDT`
*แนวโน้มยาว:* *{long_term_trend}*
*คำแนะนำ:* *{action}*
*เหตุผล:* `{reason}`
--------------------------------------
`RSI: {rsi:.2f} | MACD: {macd:.4f}`
"""
    return alert_message


async def main():
    """ฟังก์ชันหลักสำหรับรันลูปการวิเคราะห์"""
    exchange = ccxt.kucoin({
        'apiKey': KUCOIN_API_KEY,
        'secret': KUCOIN_API_SECRET,
        'options': {'adjustForTimeDifference': True},
    })
    
    try:
        await exchange.load_markets()
        print("✅ เชื่อมต่อกับ KuCoin สำเร็จ!")
    except Exception as e:
        print(f"❌ ไม่สามารถเชื่อมต่อกับ KuCoin ได้: {e}")
        await exchange.close()
        return

    while True:
        print(f"\n--- ⏱️ เริ่มรอบการวิเคราะห์ใหม่ เวลา {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        for symbol in SYMBOLS_TO_WATCH:
            df_market = await analyze_market(exchange, symbol, TIMEFRAME)
            if df_market is not None:
                df_market.name = symbol
                trading_alert = get_trading_signal(df_market)
                print(trading_alert)
                await send_telegram_message(trading_alert)
        
        print(f"--- ⏸️ จบรอบการวิเคราะห์, จะเริ่มรอบใหม่ในอีก {LOOP_INTERVAL_MINUTES} นาที ---")
        await asyncio.sleep(LOOP_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nปิดโปรแกรม...")