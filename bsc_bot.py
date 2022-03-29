#!/usr/bin/env python3
import os
import json
import math
import requests
import websocket
import _thread
import time
import telebot
import traceback
from dotenv import load_dotenv

load_dotenv()
CHAT_ID = os.getenv("BSC_CHAT_ID")
TOKEN = os.getenv("BSC_TELEGRAM_API")

bot = telebot.TeleBot(__name__)
bot.config['api_key'] = TOKEN

LAST_NOTIFICATION = {
    "AXSBNB": {
        "gap": 0.005,
        "time": 0.0,
        "last_value": 0.0
    },
    "SLPETH": {
        "gap": 0.0000001,
        "time": 0.0,
        "last_value": 0.0
    },
    "BNBBTC": {
        "gap": 0.0005,
        "time": 0.0,
        "last_value": 0.0
    }
}

def current_time() -> float:
    return float(round(time.time() * 1000))

def get_price(symbol) -> float:
    now = round(current_time())
    rq = requests.get("https://api.binance.com/api/v3/aggTrades", params={
        "symbol": f"{symbol}BIDR",
        "startTime": now - (1800 * 1000),
        "endTime": now,
        "limit": 1
    })

    # print(rq.content)
    if rq.status_code != 200:
        return 0.0

    data = rq.json()
    # print(data)
    if len(data) == 0:
        return 0.0

    return float(data[0]['p'])

def is_passed(last_time_notif) -> bool:
    gap_time = current_time() - last_time_notif
    return round(gap_time / 1000) >= 3600

def is_gap(current: float, last_value: float, value_gap: float) -> bool:
    gap = current - last_value
    return math.fabs(gap) >= value_gap

def on_message(ws, message):
    loaded_data = json.loads(message)
    raw_price = loaded_data.get("p")
    if loaded_data.get("result", False) == None:
        bot.send_message(CHAT_ID, "GET READY FOR CUAN")
        return True

    if raw_price is None:
        return True

    symbol = loaded_data.get("s")
    symbol_gap = LAST_NOTIFICATION[symbol]["gap"]
    current_price = float(raw_price)
    if is_passed(LAST_NOTIFICATION[symbol]['time']) or \
        is_gap(current_price, LAST_NOTIFICATION[symbol]['last_value'], symbol_gap):

        LAST_NOTIFICATION[symbol]['time'] = current_time()
        LAST_NOTIFICATION[symbol]['last_value'] = current_price

        text_message = f"invalid symbol: {symbol}"
        if symbol == "SLPETH":
            eth_price = get_price("ETH")
            current_bidr = round(eth_price * current_price)
            text_message = f"👛 SLP_ETH: {raw_price}\n💵 SLP_BIDR: {current_bidr:,}\n💰 ETH_BIDR: {eth_price:,}"
        elif symbol == "BNBBTC":
            btc_price = get_price("BTC")
            current_bidr = round(btc_price * current_price)
            text_message = f"💰BNB_BTC: {raw_price}\n💵 BNB_BIDR: {current_bidr:,}\n💎 BTC_BIDR: {btc_price:,}"
        elif symbol == 'AXSBNB':
            bnb_price = get_price("BNB")
            current_bidr = round(bnb_price * current_price)
            text_message = f"🔷 AXS_BNB: {raw_price}\n💵 AXS_BIDR: {current_bidr:,}\n🍁 BNB_BIDR: {bnb_price:,}"

        bot.send_message(CHAT_ID, text_message)

def on_error(ws, error):
    tb = traceback.format_exc()
    if type(error) is KeyboardInterrupt:
        bot.send_message(CHAT_ID, "BOT STOPPED")
    else:
        bot.send_message(CHAT_ID, f"BOT ERROR\n{error}\n\n{tb}")

def on_close(ws, close_status_code, close_msg):
    bot.send_message(CHAT_ID, "BOT OFF")

def on_open(ws):
    def run(*args):
        params = []
        for symbol in LAST_NOTIFICATION.keys():
            params.append(f"{symbol.lower()}@aggTrade")
        ws.send(json.dumps({"method": "SUBSCRIBE", "id": 1, "params": params}))
        bot.send_message(CHAT_ID, f"BOT STARTED\n\n- " + "\n- ".join(params))
    _thread.start_new_thread(run, ())

if __name__ == "__main__":
    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/cuanwatcher",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    ws.run_forever()
