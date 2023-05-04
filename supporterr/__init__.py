from supporterr.supporterr import Supporterr


async def setup(bot):
    n = Supporterr(bot)
    await bot.add_cog(n)
