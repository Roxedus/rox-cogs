# Bot Packages
import discord
from redbot.core import checks, commands
from redbot.core.bot import Red

import logging
import zipfile
from io import BytesIO


class Saverr(commands.Cog):
    """
    Saves stuff
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.log = logging.getLogger("red.roxcogs.saverr")
        self.log.setLevel(logging.INFO)

    @checks.admin_or_permissions(manage_emojis=True)
    @commands.command()
    async def zip_emoji(self, ctx):
        """
        Saves the emojis to zip
        """
        mem_zip = BytesIO()
        self.log.info("%s started saving emojis" % ctx.author.name)
        async with ctx.typing():
            with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for guild in self.bot.guilds:
                    self.log.info("Saving emojis for %s" % guild.name)
                    for emoji in guild.emojis:
                        ext = "png"
                        if emoji.animated:
                            ext = "gif"
                        zf.writestr(f"{guild.name}/{emoji.name}.{ext}", await emoji.url.read())
            mem_zip.seek(0)
            file = discord.File(fp=mem_zip, filename="Emoji.zip")
            await ctx.send(file=file)
