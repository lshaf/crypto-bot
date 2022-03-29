#!/usr/bin/env python
import os
import time
import math
import telebot
import traceback
import requests as req
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
CHAT_ID = os.getenv("WAX_CHAT_ID")
TOKEN = os.getenv("WAX_TELEGRAM_API")

bot = telebot.TeleBot(__name__)
bot.config['api_key'] = TOKEN

# you can get the id here https://wax.alcor.exchange/api/markets
LAST_RUN = -1
WATCHER_ID = {
    "TLM.WAX": {
        "icon": "🎓",
        "id": 26,
        "gap": 0.02,
        "time": 0,
        "last_price": 0
    },
    "DUST.WAX": {
        "icon": "✨",
        "id": 19,
        "gap": 0.001,
        "time": 0,
        "last_price": 0
    },
}


def current_time() -> float:
    return float(round(time.time() * 1000))

def is_passed(last_time_notif) -> bool:
    gap_time = current_time() - last_time_notif
    return round(gap_time / 1000) >= 3600

def over_gap(current: float, pair: str) -> bool:
    last_value = WATCHER_ID[pair]['last_price']
    value_gap = WATCHER_ID[pair]['gap']
    gap = current - last_value
    return math.fabs(gap) >= value_gap

def get_deals(id):
    url = f"https://wax.alcor.exchange/api/markets/{id}/deals"
    return req.get(url, params={"limit": 10})

def run_check():
    for [pair, token] in WATCHER_ID.items():
        detail = get_deals(token['id'])
        if detail.status_code != 200:
            bot.send_message(CHAT_ID, f"FAIL to get pair {pair}")
            continue
        
        data = detail.json()
        if len(data) == 0:
            continue

        current_price = data[0]['unit_price']
        if not is_passed(token['time']) and not over_gap(current_price, pair):
            continue

        WATCHER_ID[pair]['time'] = current_time()
        WATCHER_ID[pair]['last_price'] = current_price

        [name, wax] = pair.split(".")
        message = f"{token['icon']} {pair}\n\n" \
                  f"1 {name} = {current_price} {wax}\n" \
                  f"1 {wax} = {1/current_price} {name}"
        bot.send_message(CHAT_ID, message)



if __name__ == '__main__':
    bot.send_message(CHAT_ID, f"[BOT START]\n" + "\n".join(WATCHER_ID.keys()))
    RUNNING = True
    while RUNNING:
        try:
            time.sleep(1)
            cur_min = int(datetime.now().strftime("%M"))
            if cur_min % 5 == 0 and LAST_RUN != cur_min:
                LAST_RUN = cur_min
                run_check()

        except KeyboardInterrupt:
            RUNNING = False
            bot.send_message(CHAT_ID, "Keyboard Interupt")
        except Exception as e:
            RUNNING = False
            tb = traceback.format_exc()
            bot.send_message(CHAT_ID, f"[BOT ERROR]\n{e}\n\n{tb}")
        