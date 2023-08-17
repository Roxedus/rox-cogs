from threadmgmt.threadmgmt import ThreadManagement


async def setup(bot):
    n = ThreadManagement(bot)
    await bot.add_cog(n)
