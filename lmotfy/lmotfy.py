# Bot Packages
import discord
from redbot.core import commands
from redbot.core.bot import Red

import asyncio
import json
import logging
import urllib.request
import urllib.parse
from typing import Optional

import feedparser
from lunr import lunr, index


class Lmotfy(commands.Cog):
    """
    Let Me Orange That For You
    """

    def __init__(self, bot):
        self.bot: Red = bot

        cacher = self.Cacher(self)
        self.bot.loop.create_task(cacher.loop())

        self._headers = {'User-Agent': 'HawkBot'}
        self._orange = "https://theorangeone.net"
        self._orange_lunr = f"{self._orange}/search/index.json"
        self._orange_rss = f"{self._orange}/posts/index.xml"

        self.log = logging.getLogger("red.roxcogs.lmotfy")
        self.log.setLevel(logging.INFO)

    @commands.command(name="lmotfy", aliases=["orange"])  # , usage="<prefix> <search_query>"
    async def lmotfy(self, ctx, *, words: Optional[str]):
        """
        Let Me Orange That For You
        """

        async with ctx.typing():

            matches = self._idx.search(words)

            qString = urllib.parse.quote_plus(words)

            avatar = self.bot.user.avatar_url_as(format=None, static_format="png", size=1024)
            embed = discord.Embed(color=0xF97C00, url=f"{self._orange}/search?q={qString}")
            embed.set_author(name=self.bot.user.name, icon_url=avatar)
            embed.title = f"Here is the results of the search for `{words}`"

            matchMap = {"score": 0, "count": 0}

            for match in matches:
                matchMap["count"] += 1
                matchMap["score"] = match["score"]

                post = self.posts[match["ref"]]

                embed.add_field(name=post['title'],
                                value=f"{post['content'][:100]}\n\nScore: {match['score']}\n[Link]({post['link']})",
                                inline=False)

                if matchMap["count"] >= 7:
                    break
                if matchMap["score"] < 14:
                    break

            await ctx.send(embed=embed)

    def _get_index(self):
        try:

            feed = feedparser.parse(self._orange_rss)
            posts = {x["title"]: {"link": x["link"], "description": x["description"]} for x in feed.entries}

            with urllib.request.urlopen(self._orange_lunr) as response:
                data = json.loads(response.read().decode())
                data = [i for i in data if posts.get(i["title"])]

                idx = lunr(
                    ref='id',
                    fields=[dict(field_name='title', boost=10), 'content'],
                    documents=data
                )
                self._idx = index.Index.load(idx.serialize())

            self.posts = {x["id"]: {"content": posts[x["title"]]["description"], "title": x["title"],
                                    "link": posts[x["title"]]["link"]} for x in data}
        except Exception:
            pass

    class Cacher():
        def __init__(self, bot):
            self.bot = bot

        async def loop(self):
            while True:
                self.bot._get_index()
                await asyncio.sleep(int(60*60*12))
