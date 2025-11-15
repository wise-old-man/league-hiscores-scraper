#!/usr/bin/env python3

import asyncio
from aiohttp import ClientSession
import typing as t
import json
from pathlib import Path
from main import fetch_hiscore_players, submit_updates, BROWSER_USER_AGENT, DELAY, LOGGER, NOT_ALL_METRICS, HiscorePlayer


#########################################################
# START Configuration
#########################################################

RANK_SKIP = 50 # one page

LAST_RANKS_FILE = "last_ranked_99s.json"

XP_FOR_99 = 13_034_431

#########################################################
# END Configuration
#########################################################

async def find_last_99s(session: ClientSession) -> t.List[HiscorePlayer]:
    if (Path(LAST_RANKS_FILE).is_file()):
        with open(LAST_RANKS_FILE, "r") as f:
            last_ranks = json.load(f)
    else:
        last_ranks = {}

    last_players: t.List[HiscorePlayer] = []

    for skill in NOT_ALL_METRICS:
        LOGGER.info(f"Finding last player with level 99 for {skill.name}.")

        last_rank = 0
        if skill.name in last_ranks:
            last_rank = last_ranks[skill.name]

        last_player: HiscorePlayer | None = None

        found_last_99 = False
        while not found_last_99:
            hiscore_page = await fetch_hiscore_players(session, skill, last_rank)

            if not hiscore_page:
                continue
            
            if hiscore_page[0].score >= XP_FOR_99 and hiscore_page[-1].score < XP_FOR_99:
                current_last = hiscore_page[0]
                for player in hiscore_page[1:]:
                    if player.score <= current_last.score and player.score >= XP_FOR_99:
                        current_last = player
                    
                last_ranks[skill.name] = current_last.rank - 1
                last_player = current_last
                found_last_99 = True
            elif hiscore_page[-1].score >= XP_FOR_99:
                last_rank = hiscore_page[-1].rank - 1
                last_ranks[skill.name] = last_rank
                last_player = hiscore_page[-1]
            else:
                found_last_99 = True
                LOGGER.info(f"No 99 found, for {skill.name}.")

            await asyncio.sleep(DELAY)

        if last_player:
            last_players.append(last_player)
            LOGGER.info(
                f"Found last ranked player, {last_player.name}, for {skill.name} on rank {last_player.rank}.")

    # Write last ranks to file for use at next scrape
    data = json.dumps(last_ranks, indent=4)
    with open(LAST_RANKS_FILE, "w") as f:
        LOGGER.info(f"Writing last ranks to file...")
        f.write(data)
    
    return last_players


async def main() -> None:
    LOGGER.info("*" * 64)
    LOGGER.info("WOM Last 99 Finder starting...")

    session = ClientSession(headers={"User-Agent": BROWSER_USER_AGENT})
    last_players = await find_last_99s(session)
    await session.close()

    LOGGER.info("Last 99 Finder complete")

    if last_players:
        await submit_updates(last_players)
    LOGGER.info("*" * 64)


if __name__ == "__main__":
    asyncio.run(main())
