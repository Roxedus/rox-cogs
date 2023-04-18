# Bot Packages
import discord
from redbot.core import commands
from redbot.core.bot import Red

import datetime
import logging
import urllib.parse
import urllib.request
from email import header
from pprint import pprint
from typing import Optional
from wsgiref import headers

import aiohttp


class Lmotfy(commands.Cog):
    """
    Let Me Orange That For You
    """

    def __init__(self, bot):
        self.bot: Red = bot

        self._headers = {'User-Agent': 'HawkBot'}
        self.orange_session = aiohttp.ClientSession()
        self._orange = "https://theorangeone.net"
        self._orange_api = f"{self._orange}/api/lmotfy"

        self.log = logging.getLogger("red.roxcogs.lmotfy")
        self.log.setLevel(logging.INFO)

    async def get_result(self, query: str):
        """Calls the api to fetch results"""
        params = {"search": query}
        async with self.orange_session.get(self._orange_api, params=params, timeout=3, headers=self._headers) as response:
            assert response.status == 200
            return await response.json()

    @commands.command(name="lmotfy", aliases=["orange"])  # , usage="<prefix> <search_query>"
    async def lmotfy(self, ctx, *, words: Optional[str]):
        """
        Let Me Orange That For You
        """

        async with ctx.typing():

            matches = await self.get_result(words)

            avatar = self.bot.user.display_avatar.replace(static_format="png", size=1024).url
            embed = discord.Embed(color=0xF97C00, url=f"{self._orange}/search/?q={urllib.parse.quote(words)}")
            embed.set_author(name=self.bot.user.name, icon_url=avatar)
            embed.title = f"Here is the results of the search for `{words}`"

            if not matches["results"]:
                embed.title = f"Found no results of the search for `{words}`"
                embed.url = "https://theorangeone.net/hawkfoundnothing/"
                embed.description = ":shrug:"
                return await ctx.send(embed=embed)

            count = 0

            for match in matches["results"]:
                count += 1
                postTime = int(datetime.datetime.strptime(
                    match["date"], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name=match["title"],
                                value=f"{'.'.join(match['summary'].split('.')[:2])}.\n\n[Link]({match['full_url']})\nPosted at: <t:{postTime}:D>",
                                inline=False)

                if count >= 7:
                    break

            await ctx.send(embed=embed)
