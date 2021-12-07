from lmotfy.lmotfy import Lmotfy


def setup(bot):
    n = Lmotfy(bot)
    bot.add_cog(n)
