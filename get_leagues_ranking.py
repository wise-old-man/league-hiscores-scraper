import os
import requests
import json
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import time

OSRS_API_URL = "https://secure.runescape.com/m=hiscore_oldschool_seasonal/ranking.json?table=0&category=1&size=50&toprank={}"
WOM_API_URL = "https://api.wiseoldman.net/league/players/{}"
LOGS_FILE = "logs/logs.txt"
LAST_RANK = 409210
SUCCESS_RESP = (201, 200)
HEADERS = {"User-Agent": "leagues-scrapper-bot/1.0"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_FILE),
        logging.StreamHandler(),
    ],
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(requests.RequestException),
)
def post_player_to_api(name):
    encoded_name = requests.utils.quote(name)
    resp = requests.post(WOM_API_URL.format(encoded_name), headers=HEADERS)
    if resp.status_code not in SUCCESS_RESP:
        raise requests.RequestException(
            f"Failed to post player {name} to API. Status Code: {resp.status_code}"
        )


def save_curr_rank(curr_rank):
    with open("data/last_rank.txt", "w") as f:
        f.write(str(curr_rank))


@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(120),
)
def get_players(curr_rank):
    resp = requests.get(OSRS_API_URL.format(curr_rank))
    players = resp.json()
    if not resp.ok or not players:
        raise ValueError(
            f"Failed to fetch players from API. Status Code: {resp.status_code}"
        )
    return players


def main():
    try:
        if not os.path.exists("data/last_rank.txt"):
            with open("data/last_rank.txt", "w") as f:
                f.write("0")
        with open("data/last_rank.txt", "r") as f:
            content = f.read().strip()

        curr_rank = int(content) if content else 0
        logging.info(f"Starting from rank {curr_rank}.")

        while curr_rank < LAST_RANK:
            players = get_players(curr_rank)

            for player in players:
                try:
                    post_player_to_api(player.get("name"))
                    time.sleep(0.5)
                except:
                    logging.warning(f"Failed to post the player: {player.get('name')}")
            save_curr_rank(curr_rank)
            if curr_rank % 1000 == 0:
                logging.info(f"Processed rank page: {curr_rank}.")
            curr_rank += 50
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        save_curr_rank(curr_rank)
        logging.info(f"Saved last rank {curr_rank} to file.")
        raise e


if __name__ == "__main__":
    main()
