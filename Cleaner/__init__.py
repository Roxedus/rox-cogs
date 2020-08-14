from Cleaner.Cleaner import Cleaner


def setup(bot):
    cog = Cleaner()
    # bot.add_listener(cog.file_sniffer, "on_message")
    bot.add_cog(cog)
