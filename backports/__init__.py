# Bot Packages
from redbot.core.bot import Red

from backports.backports import Backports

__red_end_user_data_statement__ = (
    "This cog does not store data or metadata about users."
)


async def setup(bot: Red):
    cog = Backports(bot)
    await bot.add_cog(cog)
