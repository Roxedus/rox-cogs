from notpet.notpet import Notpet


async def setup(bot):
    n = Notpet(bot)
    await bot.add_cog(n)
