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
        logging.error(
            f"Failed to post player {name} to API. Status Code: {resp.status_code}"
        )
        raise requests.RequestException(
            f"Failed to post player {name} to API. Status Code: {resp.status_code}"
        )


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
            resp = requests.get(OSRS_API_URL.format(curr_rank))
            players = resp.json() if resp.ok else []

            if not players:
                raise ValueError(f"No more players found at rank {curr_rank}.")

            for player in players:
                post_player_to_api(player.get("name"))
                time.sleep(3)

            curr_rank += 50
        logging.info(f"Processed up to rank {curr_rank}.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        with open("data/last_rank.txt", "w") as f:
            f.write(str(curr_rank))
        logging.info(f"Saved last rank {curr_rank} to file.")
        raise e


if __name__ == "__main__":
    main()
