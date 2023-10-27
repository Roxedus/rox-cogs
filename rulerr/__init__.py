from rulerr.rulerr import Rulerr

__red_end_user_data_statement__ = (
    "This cog does not store data or metadata about users."
)


async def setup(bot):
    cog = Rulerr(bot)
    await cog.migrate()
    await bot.add_cog(cog)
