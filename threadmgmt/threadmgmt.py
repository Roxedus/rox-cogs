# Bot Packages
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils import views

import logging
import asyncio

DEFAULT_SETTINGS_CHANNEL = {
    "autoclose": True,
    "close_tag": None,
}


class ThreadManagement(commands.Cog):
    """
    Manage threads in your server.
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=21346578436, force_registration=True)
        self.log = logging.getLogger("red.roxcogs.threadmgmt")
        self.log.setLevel(logging.INFO)
        self.config.register_channel(**DEFAULT_SETTINGS_CHANNEL)

    @commands.group(name="threadmgmt", aliases=["tm"])
    async def thread_group(self, ctx: commands.Context):
        """
        Options for ThreadManagement
        """

    @thread_group.group()
    async def autoclose(self, ctx: commands.Context):
        """
        Autoclose options for ThreadManagement
        """

    @autoclose.command(name="toggle")
    @checks.admin_or_permissions(manage_threads=True)
    async def toggle_channel(self, ctx: commands.Context, channel: discord.ForumChannel = None):
        """
        Toggles the Autoclose for the mentioned ForumChannel
        """
        config = self.config.channel(channel)
        state = config.autoclose
        await config.autoclose.set(not state)
        await ctx.send(f"Autoclose is now set to {not state} for {channel.mention}")

    @autoclose.command(name="tag")
    @checks.admin_or_permissions(manage_threads=True)
    async def set_tag(self, ctx: commands.Context, channel: discord.ForumChannel = None, tag: str = None):
        """
        Toggles the Autoclose for the mentioned ForumChannel
        """
        config = self.config.channel(channel)

        async def write_tag(ctx, channel, tag):
            validTags = [x.name for x in channel.available_tags]
            if tag not in validTags:
                return await ctx.send(
                    f"{tag} is not a valid tag for {channel.mention}, valid tags are `{', '.join(validTags)}`"
                )
            await config.close_tag.set(tag)
            await ctx.send(f"Autoclose tag is now set to {tag} for {channel.mention}")

        if await config.close_tag() is not None:
            view = views.ConfirmView(ctx.author)
            view.confirm_button.style = discord.ButtonStyle.red
            view.confirm_button.label = "Replace"
            view.dismiss_button.label = "Cancel"
            view.message = await ctx.send(
                f"There is already a tag set for {channel.mention}, it is `{await config.close_tag()}`, replace?",
                view=view
            )
            await view.wait()
            await view.message.delete()
            if view.result:
                await write_tag(ctx, channel, tag)
        else:
            await write_tag(ctx, channel, tag)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        """
        Listen on thread updates to see if we need to do anything.
        """
        if isinstance(before.parent, discord.ForumChannel):
            config = self.config.channel(before.parent)
            closeTag = await config.close_tag()
            if await config.autoclose() and closeTag:
                newTags = [x.name for x in after.applied_tags if x not in before.applied_tags]
                if closeTag in newTags:
                    warnMsg = await before.send(f"The thread has been tagged as {closeTag}, and will be closed.")
                    await asyncio.sleep(10)
                    if closeTag in [x.name for x in before.parent.get_thread(before.id).applied_tags]:
                        await before.edit(archived=True)
                    else:
                        await warnMsg.delete()
