import os
import requests
from lxml import html
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import json
import random

# force commit 4

BASE_URL = "https://secure.runescape.com/m=hiscore_oldschool_seasonal/a=13/overall?category_type=1&table=0&page={}"
API_URL = "https://api.wiseoldman.net/league/players/{}"
FAILED_PLAYERS_FILE = "data/failed_players.json"
LOGS_FILE = "logs/logs.txt"
SUCCESS_RESP = (201, 200)
LAST_PAGE = 16395
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.8592.1188 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.1456.1529 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.6915.1989 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.6453.1890 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.3342.1121 Mobile Safari/537.36",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_FILE),
        logging.StreamHandler(),  # can disable for no console output
    ],
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(7),
    retry=retry_if_exception_type(requests.RequestException),
)
def post_player_to_api(name, headers):
    encoded_name = requests.utils.quote(name)
    resp = requests.post(API_URL.format(encoded_name))
    if resp.status_code not in SUCCESS_RESP:
        logging.error(
            f"Failed to post player {name} to API. Status Code: {resp.status_code}"
        )
        raise requests.RequestException(
            f"Failed to post player {name} to API. Status Code: {resp.status_code}"
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(7),
    retry=retry_if_exception_type(requests.RequestException),
)
def get_page(page, headers) -> html.HtmlElement:
    hiscores_url = BASE_URL.format(page)
    response = requests.get(hiscores_url, headers)

    if response.status_code not in (SUCCESS_RESP):
        logging.error(
            f"Failed to fetch page {page}. Status Code: {response.status_code}"
        )
        raise requests.RequestException("Failed to fetch hiscores page")

    return html.fromstring(response.content)


def start_from_last_page():
    try:
        with open(FAILED_PLAYERS_FILE, "r") as file:
            failed = json.load(file)
            last_page = failed.get("last_page", 1)
            logging.info(f"Starting from last page: {last_page}")
            return last_page
    except FileNotFoundError:
        logging.info("No previous state found. Starting from page 1.")
        return 1


def save_failed_players(failed):
    with open(FAILED_PLAYERS_FILE, "w") as file:
        json.dump(failed, file)
        logging.info(f"Saved failed players to {FAILED_PLAYERS_FILE}")


def main():
    failed = {}
    page = start_from_last_page()
    total_players = 0
    no_players_found = 0
    try:

        while page < LAST_PAGE:
            headers = random.choice(USER_AGENTS)
            tree = get_page(page, headers)
            names = tree.xpath('//tr[@class="personal-hiscores__row"]/td[2]/a/text()')
            if not names:
                no_players_found += 1
                if no_players_found >= 3:
                    logging.info("No players found for 3 consecutive pages. Stopping.")
                    raise ValueError("No players found for 3 consecutive pages.")

            for name in names:
                time.sleep(3)
                post_player_to_api(name, headers)
                total_players += 1
                logging.info(f"Posted player {name} to API.")

            page += 1
            failed["last_page"] = page
            save_failed_players(failed)
        logging.info(
            f"Finished scrapping. Extracted {total_players} players and Pages: {page}."
        )
    except Exception as e:
        logging.error(
            f"An error occurred: {e}.\n Failed at page: {page}, extracted {total_players} players."
        )
        failed["last_page"] = page
        save_failed_players(failed)
        logging.info(f"Failed players: {failed}")
        logging.info(f"Saved state to {FAILED_PLAYERS_FILE}.")
        raise e


if __name__ == "__main__":
    main()
