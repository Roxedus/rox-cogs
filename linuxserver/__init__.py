from linuxserver.linuxserver import LinuxServer


async def setup(bot):
    n = LinuxServer(bot)
    await n.initialize()
    await bot.add_cog(n)
