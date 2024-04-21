# Bot Packages
import discord
from redbot.core import checks, commands
from redbot.core.bot import Red

import logging

import aiohttp


class Notpet(commands.Cog):
    """
    """

    def __init__(self, bot):
        self.bot: Red = bot

        self.pet_session = aiohttp.ClientSession()
        self._gist = "https://gist.githubusercontent.com/Dziurwa14/05db50c66e4dcc67d129838e1b9d739a/raw/spy.pet%2520accounts"

        self.log = logging.getLogger("red.roxcogs.notpet")
        self.log.setLevel(logging.INFO)

    async def get_result(self):
        """
        Calls the api to fetch results
        """
        async with self.pet_session.get(self._gist,timeout=3) as response:
            assert response.status == 200

            resp = await response.json(content_type='text/plain')

            return resp

    @commands.command()
    @commands.cooldown(1, (30 * 60), type=discord.ext.commands.BucketType.default)
    @checks.admin_or_permissions(ban_members=True)
    async def pets(self, ctx):

        foundPets = []

        allPets = await self.get_result()
        msg = await ctx.send("This may make take a few minutes")

        async with ctx.typing():
            for pet in allPets:
                try:
                    boat = await ctx.guild.fetch_member(pet)
                    foundPets.append(boat)
                except discord.NotFound:
                    pass

        embed = discord.Embed(title="Pet Overview")
        embed.description = "No spying pets found"
        if foundPets:
            mentionPets = [x.mention for x in foundPets]
            embed.description = f"Found {len(foundPets)} bots:\n"
            embed.description += ",".join(mentionPets)

        await msg.edit(content=None, embed=embed)