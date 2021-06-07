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
        default_guild = {
            "enabled": False,
            "types": ["jpg", "png", "gif", "bmp"]
        }
        default_channel = {
            "types": "Guild"
        }
        self.log = logging.getLogger("red.roxcogs.cleanerr")
        self.log.setLevel(logging.INFO)
        self.config.register_guild(**default_guild)
        self.config.register_channel(**default_channel)

    @commands.group()
    async def cleanerr(self, ctx: commands.Context):
        """
        Options for cleanerr
        """
        pass

    @cleanerr.group()
    async def channel(self, ctx: commands.Context):
        """
        Channel options for cleanerr
        """
        pass

    @channel.command(name="toggle")
    @checks.admin_or_permissions(manage_messages=True)
    async def toggle_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Toggles the cleaner for the current, or mentioned channel
        """
        if not channel:
            channel = ctx.channel
        state = await self.config.channel(channel).enabled()
        await self.config.channel(channel).enabled.set(not state)
        await ctx.send(f"Cleaner is now set to {not state} for {channel.mention}")

    @channel.command(name="ext")
    @checks.admin_or_permissions(manage_messages=True)
    async def ext_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None,
                          *, extentions: str = "guild"):
        """
        Sets the extentions for the cleaner in the current, or mentioned channel.
        If no mention is passed, it sets the Default value

        Default = Inherits the Guild default
        """

        msg = "Cleaner is set to follow the guild allowlist"

        if extentions == "guild":
            extentions = "Guild"
        else:
            extentions = list(extentions.lower().split(" "))
            msg = f"Cleaner is set to allow the files with the extentions: {', '.join(extentions)}"

        if not channel:
            channel = ctx.channel

        await self.config.channel(channel).types.set(extentions)
        await ctx.send(msg + f" for {channel.mention}")

    @cleanerr.group()
    async def guild(self, ctx: commands.Context):
        """
        Channel options for cleanerr
        """
        pass

    @guild.command(name="toggle")
    @checks.admin_or_permissions(manage_messages=True)
    async def toggle_guild(self, ctx: commands.Context):
        """
        Toggles the cleaner for the guild
        """
        state = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not state)
        await ctx.send(f"Cleaner is now set to {not state} for {ctx.guild.name}")

    @guild.command(name="ext")
    @checks.admin_or_permissions(manage_messages=True)
    async def ext_guild(self, ctx: commands.Context, *, extentions: str):
        """
        Sets the extentions for the cleaner in the guild

        Default = jpg png gif bmp
        """

        extentions = list(extentions.lower().split(" "))

        await self.config.guild(ctx.guild).types.set(extentions)
        await ctx.send(
            f"Cleaner is set to allow the files with the extentions: {', '.join(extentions)} for {ctx.guild.name}")

    @cleanerr.command(name="info")
    @checks.admin_or_permissions(manage_messages=True)
    async def info_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not channel:
            channel = ctx.channel

        channel_conf = await self.config.channel(channel).all()
        guild_conf = await self.config.guild(ctx.guild).all()

        enabled = "No (Globally)"

        if channel_conf.get('enabled', None) is not None:
            if channel_conf.get('enabled'):
                enabled = "Yes (Channel)"
            elif not channel_conf.get('enabled'):
                enabled = "No (Channel)"
        elif guild_conf.get('enabled', None):
            enabled = "Yes (Globally)"

        ext = guild_conf.get("types"), "Globally"

        if isinstance(channel_conf.get("types"), list):
            ext = channel_conf.get("types"), "Channel"

        msg = f"```\nChannel enabled: {enabled}\nAllowed types in this channel: {', '.join(ext[0])} ({ext[1]})\n```"
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        channel_types = await self.config.channel(message.channel).types()
        guild_allowed = (await self.config.guild(message.guild).all()).get('enabled', None)
        channel_allowed = (await self.config.channel(message.channel).all()).get('enabled', None)

        allowed_types = await self.config.guild(message.guild).types() if channel_types == "Guild" else channel_types
        allowed_channel = channel_allowed if channel_allowed is not None else guild_allowed

        if allowed_channel and message.attachments:
            for attachment in message.attachments:
                if attachment.filename.split(".")[-1].lower() not in allowed_types:
                    await message.delete()
                    msg_content = f"{message.author.mention} Please do not post attachments."
                    title = "This is not an image"
                    description = "To help guard our users against malware, we only allow image uploads." \
                                  "\nIf you posted logs, please upload them to " \
                                  "[0Bin](https://0bin.net) " \
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
