#!/usr/bin/env python
import os
import time
import math
import telebot
import traceback
import requests as req
from datetime import datetime
from dotenv import load_dotenv
from requests.exceptions import ConnectionError

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
        "gap": 0.2,
        "last_price": 0,
        "last_pair": 0,
        "swap_id": 0
    },
    "DUST.WAX": {
        "icon": "✨",
        "id": 19,
        "gap": 10,
        "last_price": 0,
        "last_pair": 0,
        "swap_id": 1
    },
    "LEEF.WAX": {
        "icon": "🌿",
        "id": 119,
        "swap_id": 532,
        "gap": 2000,
        "last_price": 0,
        "last_pair": 0,
    },
    "ECR.WAX": {
        "icon": "🌞",
        "id": 627,
        "swap_id": 2408,
        "gap": 8000,
        "last_price": 0,
        "last_pair": 0,
    },
    "XYTE.WAX": {
        "icon": "🪐",
        "id": 142,
        "swap_id": 634,
        "gap": 20,
        "last_price": 0,
        "last_pair": 0,
    },
}


def current_time() -> float:
    return float(round(time.time() * 1000))


def is_passed(last_time_notif) -> bool:
    gap_time = current_time() - last_time_notif
    return round(gap_time / 1000) >= 3600


def over_gap(current: float, pair: str, meta='last_price') -> bool:
    last_value = WATCHER_ID[pair][meta]
    value_gap = WATCHER_ID[pair]['gap']
    gap = current - last_value
    return math.fabs(gap) >= value_gap


def get_deals(id):
    url = f"https://wax.alcor.exchange/api/markets/{id}/deals"
    return req.get(url, params={"limit": 10})


def get_pairs(id):
    url = "https://wax.blokcrafters.io/v1/chain/get_table_rows"
    return req.post(url, json={
        "json": True,
        "code": "alcorammswap",
        "scope": "alcorammswap",
        "table": "pairs",
        "index_position": 1,
        "key_type": "",
        "lower_bound": id,
        "upper_bound": id,
        "limit": 1
    })


def get_movement_icon(var_1, var_2):
    movement_icon = "🟰"
    if var_1 > var_2:
        movement_icon = "🟥"
    elif var_1 < var_2:
        movement_icon = "🟩"

    return movement_icon


def run_market_price(pair, token):
    detail = get_deals(token['id'])
    if detail.status_code != 200:
        bot.send_message(CHAT_ID, f"FAIL to get market {pair}")
        return None

    data = detail.json()
    if len(data) == 0:
        return None

    current_price = data[0]['unit_price']
    token_pair = 1/current_price
    if not over_gap(token_pair, pair):
        return None

    movement_icon = get_movement_icon(token_pair, WATCHER_ID[pair]['last_price'])
    WATCHER_ID[pair]['last_price'] = token_pair

    [name, wax] = pair.split(".")
    message = f"📘{token['icon']}{movement_icon}\n{pair} in market\n\n" \
              f"1 {name} = {current_price:.5f} {wax}\n" \
              f"1 {wax} = {token_pair:.5f} {name}"
    bot.send_message(CHAT_ID, message)
    return True


def run_swap_price(pair, token):
    detail = get_pairs(token['swap_id'])
    if detail.status_code != 200:
        bot.send_message(CHAT_ID, f"FAIL to get pair {pair}")
        return None

    data = detail.json()
    if len(data['rows']) == 0:
        return None

    obj = data['rows'][0]
    pool_1, _ = obj['pool1']['quantity'].split(" ")
    pool_2, _ = obj['pool2']['quantity'].split(" ")
    pair_1 = float(pool_1) / float(pool_2)  # in wax
    pair_2 = float(pool_2) / float(pool_1)  # in token
    if not over_gap(pair_2, pair, 'last_pair'):
        return None

    movement_icon = get_movement_icon(pair_2, WATCHER_ID[pair]['last_pair'])
    WATCHER_ID[pair]['last_pair'] = pair_2

    [name, wax] = pair.split(".")
    message = f"💹{token['icon']}{movement_icon}\n{pair} in swap\n\n" \
              f"1 {name} = {pair_1:.5f} {wax}\n" \
              f"1 {wax} = {pair_2:.5f} {name}"
    bot.send_message(CHAT_ID, message)
    return True


def run_check():
    try:
        for [pair, token] in WATCHER_ID.items():
            run_market_price(pair, token)
            run_swap_price(pair, token)
    except ConnectionError:
        bot.send_message(CHAT_ID, f"[Connection Error] Will try again")



if __name__ == '__main__':
    bot.send_message(CHAT_ID, f"[BOT START]\n" + "\n".join(WATCHER_ID.keys()))
    RUNNING = True
    while RUNNING:
        try:
            time.sleep(1)
            cur_min = int(datetime.now().strftime("%M"))
            if (cur_min % 3 == 0 and LAST_RUN != cur_min) or LAST_RUN == -1:
                LAST_RUN = cur_min
                run_check()

        except KeyboardInterrupt:
            RUNNING = False
            bot.send_message(CHAT_ID, "Keyboard Interupt")
        except Exception as e:
            RUNNING = False
            tb = traceback.format_exc()
            bot.send_message(CHAT_ID, f"[BOT ERROR]\n{e}\n\n{tb}")
        