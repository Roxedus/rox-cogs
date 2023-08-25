# Bot Packages
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils import views
from typing import Literal, Union

import logging
import asyncio

TAG_TYPES = Literal["close", "invalid"]

DEFAULT_SETTINGS_CHANNEL = {
    "close_tag": None,
    "invalid_tag": None,
    "invalid_tag_messages": {}
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

    @thread_group.group(name="set")
    async def thread_set(self, ctx: commands.Context):
        """
        Sets options for ThreadManagement
        """

    @thread_set.command(name="tag")
    @checks.admin_or_permissions(manage_threads=True)
    async def set_tag(self, ctx: commands.Context, tag_type: TAG_TYPES = None,
                      channel: discord.ForumChannel = None, tag: Union[str, None] = None):
        """
        Set the tag for the tag_types for the mentioned ForumChannel
        """
        config = await self.config.channel(channel).get_raw(f"{tag_type}_tag")

        async def write_tag(ctx, tag_type, channel, tag):
            if tag is not None:
                validTags = [x.name for x in channel.available_tags]
                if tag not in validTags:
                    return await ctx.send(
                        f"{tag} is not a valid tag for {channel.mention}, valid tags are `{', '.join(validTags)}`"
                    )
            await self.config.channel(channel).set_raw(f"{tag_type}_tag", value=tag)
            await ctx.send(f"{tag_type.title()}-tag is now set to {tag} for {channel.mention}")

        if config is not None:
            view = views.ConfirmView(ctx.author)
            view.confirm_button.style = discord.ButtonStyle.red
            view.confirm_button.label = "Replace"
            view.dismiss_button.label = "Cancel"
            view.message = await ctx.send(
                f"There is already a {tag_type}-tag set for {channel.mention}, it is `{config}`, replace?",
                view=view
            )
            await view.wait()
            await view.message.delete()
            if view.result:
                await write_tag(ctx, tag_type, channel, tag)
        else:
            await write_tag(ctx, tag_type, channel, tag)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        """
        Listen on thread updates to see if we need to do anything.
        """
        if isinstance(before.parent, discord.ForumChannel):
            config = self.config.channel(before.parent)
            closeTag = await config.close_tag()
            invalidTag = await config.invalid_tag()
            newTags = [x.name for x in after.applied_tags if x not in before.applied_tags]
            oldTags = [x.name for x in before.applied_tags if x not in after.applied_tags]
            if not before.archived and after.archived:
                print("Thread was archived")
                return await config.invalid_tag_messages.clear_raw(before.id)
            if closeTag in newTags:
                warnMsg = await before.send(f"The thread has been tagged as {closeTag}, and will be closed.")
                await asyncio.sleep(10)
                if closeTag in [x.name for x in before.parent.get_thread(before.id).applied_tags]:
                    await before.edit(archived=True)
                else:
                    await warnMsg.delete()
                return
            if invalidTag in newTags:
                warnMsg = await before.send(
                    f"The thread has been tagged as {invalidTag} by a human, this likely happened because helpfull "
                    "information was missing from the post."
                )
                await config.invalid_tag_messages.set_raw(before.id, value=warnMsg.id)
            elif invalidTag in oldTags:
                warnMsg = await config.invalid_tag_messages.get_raw(before.id)
                if warnMsg:
                    await (await before.fetch_message(warnMsg)).delete()
                    await config.invalid_tag_messages.clear_raw(before.id)
            return
