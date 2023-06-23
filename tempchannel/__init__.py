# Bot Packages
from redbot.core.bot import Red

from tempchannel.tempchannel import TempChannel

__red_end_user_data_statement__ = (
    "This cog does not store data or metadata about users."
)


async def setup(bot: Red):
    cog = TempChannel(bot)
    await bot.add_cog(cog)
