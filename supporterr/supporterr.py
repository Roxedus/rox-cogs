# Bot Packages
import discord
from redbot.core import commands
from redbot.core.utils.embed import randomize_colour
from redbot.core.bot import Red

import logging
from typing import Optional


class Supporterr(commands.Cog):
    """
    Various commands for support
    """

    def __init__(self, bot):
        self.bot: Red = bot

        self.log = logging.getLogger("red.roxcogs.supporter")
        self.log.setLevel(logging.INFO)

    @commands.guild_only()
    @commands.command(name="f12")  # , usage="<prefix> <search_query>"
    async def _f12(self, ctx, user: Optional[discord.Member] = None, *, tab: Optional[str] = "console"):
        """
        Command to promt the user to send the output of their browser-console
        """

        msg = f"Hey{' ' + user.mention if user else ''}! Please post a screenshot"\
              ", or the text showing up in your browser-console"
        title = "Hey! Please show your browser-console"
        txt = "Press the `f12` key on your keyboard, or `CTRL + SHIFT + I`.\n" \
              f"Then switch to the **{tab.lower()}** tab.\n" \
              "Paste, or screenshot the contents of the tab"
        embed = discord.Embed(title=title, colour=user.colour if user else ctx.author.colour)
        embed.description = txt
        embed.add_field(name="Chrome", inline=True,
                        value="[HOW TO](https://developers.google.com/web/tools/chrome-devtools/open)")
        embed.add_field(name="Firefox", inline=True,
                        value="[HOW TO](https://developer.mozilla.org/en-US/docs/Tools/Browser_Console)")
        embed.add_field(name="Safari", inline=True,
                        value="[HOW TO](https://support.apple.com/guide/safari/"
                              "use-the-developer-tools-in-the-develop-menu-sfri20948/mac)")
        if embed.colour.value == 0:
            embed = randomize_colour(embed=embed)
        await ctx.send(msg, embed=embed)

    @commands.guild_only()
    @commands.command(name="paste", aliases=["share-nginx"])
    async def _paste_nginx(self, ctx, user: Optional[discord.Member] = None):
        """
        Command to promt the user to send their nginx config
        """

        msg = f"Hey{' ' + user.mention if user else ''}! Please share your nginx config"
        title = "Hey! Please show your nginx config"
        txt = "Please post your Nginx config using one of the following methods:\n" \
            "**1 -** Using nginx pastebin: <https://paste.nginx.org/>\n" \
            "**2 -** Using pastebin: <https://pastebin.com/>\n" \
            "**3 -** Using discord markdown, by typing:\n\n" \
            "\\```nginx\n" \
            "\\<code>\n" \
            "\\```\n\n" \
            "If you have any includes, like proxy.conf, make sure to post that too.\n" \
            "**Make sure to replace server_name to example.com, also remove any WAN-IP addresses. \n" \
            "Otherwise the message will be removed by a moderator.**"
        embed = discord.Embed(title=title, colour=user.colour if user else ctx.author.colour)
        embed.description = txt
        embed.add_field(name="Gist", inline=True, value="[GIST](https://gist.github.com/)")
        embed.add_field(name="Nginx Pastebin", inline=True, value="[Nginx](https://paste.nginx.org/)")
        embed.add_field(name="Pastebin", inline=True, value="[Pastebin](https://pastebin.com)")
        if embed.colour.value == 0:
            embed = randomize_colour(embed=embed)
        await ctx.send(msg, embed=embed)
