# Bot Packages
import discord
from redbot.core import commands, modlog
from redbot.core.bot import Red

import logging


class Aaa(commands.Cog):
    """
    aaaaaaaa
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.log = logging.getLogger("red.roxcogs.aaa")
        self.log.setLevel(logging.INFO)

    @commands.command()
    @commands.guild_only()
    @commands.guildowner()
    async def modlog_unban(self, ctx, mod_id: int):
        """
        Unbans every ban given by a moderator
        """
        dBans = [entry.user.id async for entry in ctx.guild.bans(limit=2000)]
        mlBans = [entry for entry in await modlog.get_all_cases(ctx.guild, self.bot) if entry.action_type == "ban"]

        banEntry = []

        for ban in mlBans:
            _id = None
            if isinstance(ban.user, int):
                _id = ban.user
            elif isinstance(ban.user, discord.abc.User):
                _id = ban.user.id
            if _id in dBans:
                banEntry.append([_id, ban])

        unbanCounter = 0

        for user, entry in banEntry:
            mod = None
            if isinstance(entry.moderator, int):
                mod = entry.moderator
            elif isinstance(entry.moderator, discord.abc.User):
                mod = entry.moderator.id
            if mod == mod_id:
                await ctx.guild.unban(discord.Object(user))
                unbanCounter += 1

        await ctx.send(f"Unbanned {unbanCounter} users")
