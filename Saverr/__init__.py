from Saverr.Saverr import Saverr

__red_end_user_data_statement__ = (
    "This cog does not store data or metadata about users."
)


def setup(bot):
    cog = Saverr(bot)
    bot.add_cog(cog)
