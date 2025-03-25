import os
import json
import time
import asyncio
import aiohttp
from telegram import Bot

# ✅ Load Environment Variables Securely
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# ✅ Validate Credentials Before Running
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
    raise ValueError("❌ Missing Telegram API credentials. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID as environment variables.")

# ✅ Initialize Telegram Bot AFTER Validation
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# API URLs
PERIOD_API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M.json"
RESULT_API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"

current_prediction = None
consecutive_losses = 0

# ✅ Helper Functions
def get_big_small(number):
    return "SMALL" if number in [0, 1, 2, 3, 4] else "BIG"

def get_red_green(number):
    return "RED" if number in [0, 2, 4, 6, 8] else "GREEN"

async def fetch_data(url, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            text = await response.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                print("[ERROR] JSON Decode Error")
                return None

async def fetch_latest_results():
    data = await fetch_data(RESULT_API_URL)
    return data["data"].get("list", []) if data and "data" in data else []

async def get_current_period():
    data = await fetch_data(PERIOD_API_URL)
    return data["current"] if data and "current" in data else None

async def send_prediction():
    global current_prediction
    current_info = await get_current_period()
    if not current_info:
        return
    
    current_period = current_info["issueNumber"]
    results = await fetch_latest_results()
    
    if not results:
        return
    
    # ✅ Predict Based on Latest Results
    latest_result = results[0]
    prediction_mode = "bs" if get_big_small(int(latest_result["number"])) == get_big_small(int(results[1]["number"])) else "color"
    prediction = get_big_small(int(latest_result["number"])) if prediction_mode == "bs" else get_red_green(int(latest_result["number"]))

    message = f"""
🏆 <b>JALWA WINGO 1MIN</b> 🏆

🔓 <b>PERIOD ID</b> - {current_period} - <b>{prediction}</b>

<i><b>Game Link:</b></i> <a href="https://www.jalwa.live/#/">https://www.jalwa.live</a>
"""

    sent_message = await bot.send_message(TELEGRAM_CHANNEL_ID, message, parse_mode="HTML")
    current_prediction = {"period": current_period, "prediction": prediction, "mode": prediction_mode, "message_id": sent_message.message_id}

async def update_result():
    global current_prediction, consecutive_losses
    if not current_prediction:
        return

    results = await fetch_latest_results()
    latest = results[0] if results else None

    if latest and latest["issueNumber"] == current_prediction["period"]:
        actual = get_big_small(int(latest["number"])) if current_prediction["mode"] == "bs" else get_red_green(int(latest["number"]))

        if actual == current_prediction["prediction"]:
            await bot.send_sticker(
                chat_id=TELEGRAM_CHANNEL_ID,
                sticker="CAACAgUAAxkBAAEyWQNnx1REzwS6iG841FtNqHkaTtkthQACWxUAAqoa4VZursiDNO2CLDYE",
                reply_to_message_id=current_prediction["message_id"]
            )
            consecutive_losses = 0
        else:
            consecutive_losses += 1
            if consecutive_losses >= 3:
                await bot.send_message(TELEGRAM_CHANNEL_ID, "⚠️ <b><u>Chart not stable</u> 🥹</b>\n\n<b>Wait for 2 minutes 🤩</b>", parse_mode="HTML")
                await asyncio.sleep(120)
                consecutive_losses = 0

        current_prediction = None

async def main():
    while True:
        start_time = time.time()  # Mark the start of the cycle

        # ✅ Step 1: Wait for the start of a new minute
        elapsed = start_time % 60
        if elapsed > 0:
            await asyncio.sleep(60 - elapsed)

        # ✅ Step 2: Update the result at 2s
        await asyncio.sleep(2)  
        print(f"[INFO] Updating result at {time.strftime('%H:%M:%S')}")
        await update_result()

        # ✅ Step 3: Fetch current period & send prediction at 3s
        await asyncio.sleep(1)  
        print(f"[INFO] Fetching current period & sending prediction at {time.strftime('%H:%M:%S')}")
        await send_prediction()

        # ✅ Ensure exactly 60s cycle
        elapsed = time.time() - start_time
        await asyncio.sleep(max(60 - elapsed, 0))

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
