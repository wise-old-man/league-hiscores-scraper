import requests
from lxml import html
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


base_url = "https://secure.runescape.com/m=hiscore_oldschool_seasonal/a=13/overall?category_type=1&table=0&page={}"
api_url = "https://api.wiseoldman.net/v2/players/{}"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(7),
    retry=retry_if_exception_type(requests.RequestException),
)
def post_player_to_api(name):
    encoded_name = requests.utils.quote(name)
    resp = requests.post(api_url.format(encoded_name))

    if resp.status_code == 200:
        logging.info(f"Player {name} found and posted to API")
        return True
    else:
        logging.warning(f"Player {name} not found (status: {resp.status_code})")
        return False


def main():
    try:
        page = 1
        total_players = 0

        while True:
            hiscores_url = base_url.format(page)
            response = requests.get(hiscores_url)

            if response.status_code != 200:
                logging.error(
                    f"Failed to fetch page {page}. Status Code: {response.status_code}"
                )
                raise requests.RequestException("Failed to fetch hiscores page")

            tree = html.fromstring(response.content)
            names = tree.xpath('//tr[@class="personal-hiscores__row"]/td[2]/a/text()')

            if not names:
                logging.info(f"No more names found. Stopping at page {page}.")
                break

            for name in names:
                try:
                    time.sleep(2)
                    if post_player_to_api(name):
                        total_players += 1
                except requests.RequestException as e:
                    logging.error(f"Error while posting player {name} to API: {e}")

            next_page = tree.xpath(
                '//a[contains(@class, "personal-hiscores__pagination-arrow--down")]/@href'
            )

            if not next_page:
                break

            page += 1
        logging.info(
            f"Finished scrapping. Extracted {total_players} players and Pages: {page}."
        )
    except Exception as e:
        logging.error(
            f"An error occurred: {e}.\n Failed at page: {page}, extracted {total_players} players."
        )
        raise e


if __name__ == "__main__":
    main()
