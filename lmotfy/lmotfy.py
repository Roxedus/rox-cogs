# Bot Packages
import discord
from redbot.core import commands
from redbot.core.bot import Red

import asyncio
import json
import logging
import urllib.request
from typing import Optional

from fuzzywuzzy import fuzz


class Lmotfy(commands.Cog):
    """
    Let Me Orange That For You
    """

    def __init__(self, bot):
        self.bot: Red = bot

        cacher = self.Cacher(self)
        self.bot.loop.create_task(cacher.loop())

        self._headers = {'User-Agent': 'HawkBot'}
        self._orange = "https://theorangeone.net/index.json"

        self.log = logging.getLogger("red.roxcogs.lmotfy")
        self.log.setLevel(logging.INFO)

    @commands.command(name="lmotfy", aliases=["orange"])  # , usage="<prefix> <search_query>"
    async def lmotfy(self, ctx, *, words: Optional[str]):
        """
        Let Me Orange That For You
        """

        async with ctx.typing():

            scores = []
            for index, item in enumerate(self._data):
                values = list(item.values())
                ratios = [fuzz.partial_ratio(str(words).lower(), str(value).lower()) for value in values]
                scores.append({"index": index, "score": max(ratios)})

            filtered_scores = [item for item in scores if item['score'] >= 40]
            sorted_filtered_scores = sorted(filtered_scores, key=lambda k: k['score'], reverse=True)
            filtered_list_of_dicts = [self._data[item["index"]] for item in sorted_filtered_scores]

            avatar = self.bot.user.avatar_url_as(format=None, static_format="png", size=1024)
            embed = discord.Embed(color=0xF97C00)
            embed.set_author(name=self.bot.user.name, icon_url=avatar)

            msg = ""
            for i in range(7):
                print(f"{sorted_filtered_scores[i]=}, {filtered_list_of_dicts[i]=}")

                msg += "[" + filtered_list_of_dicts[i]["title"] + "](" + filtered_list_of_dicts[i]["url"] + ")\n"

            embed.description = msg

        await ctx.send(embed=embed)

    async def _get_index(self):
        with urllib.request.urlopen(self._orange) as response:
            self._data = json.load(response)

    class Cacher():
        def __init__(self, bot):
            self.bot = bot

        async def loop(self):
            while True:
                await self.bot._get_index()
                await asyncio.sleep(int(60*60*12))
