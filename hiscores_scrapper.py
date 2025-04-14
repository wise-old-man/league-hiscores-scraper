import os
import requests
from lxml import html
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import json


BASE_URL = "https://secure.runescape.com/m=hiscore_oldschool_seasonal/a=13/overall?category_type=1&table=0&page={}"
API_URL = "https://api.wiseoldman.net/v2/players/{}"
FAILED_PLAYERS_FILE = "data/failed_players.json"
LOGS_FILE = "logs/logs.txt"
SUCCESS_RESP = (201, 200)


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
def post_player_to_api(name):
    encoded_name = requests.utils.quote(name)
    resp = requests.post(API_URL.format(encoded_name))
    if resp.status_code not in (SUCCESS_RESP):
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
    try:
        failed = {}
        page = start_from_last_page()
        total_players = 0

        while True:
            tree = get_page(page)
            names = tree.xpath('//tr[@class="personal-hiscores__row"]/td[2]/a/text()')

            if not names:
                logging.info(f"No more names found. Stopping at page {page}.")
                break

            for name in names:
                post_player_to_api(name)
                total_players += 1
                logging.info(f"Posted player {name} to API.")

            next_page = tree.xpath(
                '//a[contains(@class, "personal-hiscores__pagination-arrow--down")]/@href'
            )

            if not next_page:
                failed["last_page"] = page
                save_failed_players(failed)
                logging.info(f"No next page found. Stopping at page {page}.")
                break

            page += 1
        logging.info(
            f"Finished scrapping. Extracted {total_players} players and Pages: {page}."
        )
        failed["last_page"] = page
        save_failed_players(failed)
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
