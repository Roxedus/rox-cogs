from lmotfy.lmotfy import Lmotfy


async def setup(bot):
    n = Lmotfy(bot)
    await bot.add_cog(n)
