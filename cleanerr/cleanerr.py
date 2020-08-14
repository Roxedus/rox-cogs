# Bot Packages
import discord
from redbot.core import Config, checks, commands

import logging
from typing import Optional


class Cleanerr(commands.Cog):
    """
    Deletes messages with attachments that are not images.
    """

    def __init__(self):
        self.config = Config.get_conf(self, identifier=2592823300)
        default_allowed = {
            "enabled": False,
            "types": ["jpg", "png", "gif", "bmp"]
        }
        self.log = logging.getLogger("red.roxcogs.cleaner")
        self.log.setLevel(logging.INFO)
        self.config.register_channel(**default_allowed)

    @commands.group()
    async def cleanerr(self, ctx: commands.Context):
        """
        Options for cleanerr
        """
        pass

    @cleanerr.command(name="toggle")
    @checks.admin_or_permissions(manage_messages=True)
    async def toggle_channel(self, ctx, channel: discord.TextChannel = None):
        """
        Toggles the cleaner for the current, or mentioned channel
        """
        if not channel:
            channel = ctx.channel
        state = await self.config.channel(channel).enabled()
        await self.config.channel(channel).enabled.set(not state)
        await ctx.send(f"Cleaner is now set to {not state} for {channel.mention}")

    @cleanerr.command(name="ext")
    @checks.admin_or_permissions(manage_messages=True)
    async def ext_channel(self, ctx, channel: Optional[discord.TextChannel] = None, *, extentions: str):
        """
        Sets the extentions for the cleaner in the current, or mentioned channel

        Default= jpg png gif bmp
        """

        extentions = list(extentions.split(" "))

        if not channel:
            channel = ctx.channel

        await self.config.channel(channel).types.set(extentions)
        await ctx.send(
            f"Cleaner is set to delete the files with the extentions: {', '.join(extentions)} for {channel.mention}")

    @cleanerr.command(name="info")
    @checks.admin_or_permissions(manage_messages=True)
    async def info_channel(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            channel = ctx.channel
        conf = await self.config.channel(channel).all()
        msg = "```\n"
        for k, v in conf.items():
            msg += k + ": " + str(v) + "\n"
        msg += "\n```"
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message):
        allowed_types = await self.config.channel(message.channel).types()
        allowed_channel = await self.config.channel(message.channel).enabled()
        if not message.author.bot and allowed_channel and message.attachments:
            for attachment in message.attachments:
                if attachment.filename.split(".")[-1] not in allowed_types:
                    await message.delete()
                    msg_content = f"{message.author.mention} Please do not post attachments."
                    title = "This is not an image"
                    description = "To help guard our users against malware, we only allow image uploads." \
                                  "\nIf you posted logs, please upload them to " \
                                  "[Pastebin](https://pastebin.com) " \
                                  "or [Gist](https://gist.github.com/)" \
                                  "\n**do not upload** the file as an attachment."
                    foot = f"Called by {message.author}"
                    embed = discord.Embed(
                        title=title, colour=message.author.colour, description=description)
                    embed.set_footer(
                        text=foot, icon_url=message.author.avatar_url)
                    await message.channel.send(content=msg_content, embed=embed)
                    self.log.info("%s posted a prohibited attatchment in %s:%s" %
                                  (message.author.name, message.guild.name, message.channel.name))
