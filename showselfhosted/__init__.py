# Bot Packages
from redbot.core.bot import Red

from showselfhosted.showselfhosted import ShowSelfHosted

__red_end_user_data_statement__ = (
    "This cog does not store data or metadata about users."
)


async def setup(bot: Red):
    cog = ShowSelfHosted(bot)
    await bot.add_cog(cog)
