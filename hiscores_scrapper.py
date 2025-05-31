import os
import requests
from lxml import html
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import json

# force commit 4

BASE_URL = "https://secure.runescape.com/m=hiscore_oldschool_seasonal/a=13/overall?category_type=1&table=0&page={}"
API_URL = "https://api.wiseoldman.net/league/players/{}"
FAILED_PLAYERS_FILE = "data/failed_players.json"
LOGS_FILE = "logs/logs.txt"
SUCCESS_RESP = (201, 200)
LAST_PAGE = 16395
API_HEADERS = {"User-Agent": "leagues-scrapper-bot/1.0"}

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
    wait=wait_fixed(7),
    retry=retry_if_exception_type(requests.RequestException),
)
def post_player_to_api(name):
    encoded_name = requests.utils.quote(name)
    resp = requests.post(API_URL.format(encoded_name), headers=API_HEADERS)
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
def get_page(page) -> html.HtmlElement:
    hiscores_url = BASE_URL.format(page)
    response = requests.get(hiscores_url)

    if response.status_code not in SUCCESS_RESP:
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
            tree = get_page(page)
            names = tree.xpath('//tr[@class="personal-hiscores__row"]/td[2]/a/text()')

            if not names:
                raise ValueError("No players found check the page structure")

            for name in names:
                time.sleep(3)
                post_player_to_api(name)
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
        raise


if __name__ == "__main__":
    main()
