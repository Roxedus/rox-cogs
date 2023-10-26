# Bot Packages
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils import views

import asyncio
import logging
from datetime import timedelta
from typing import Literal, Union

TAG_TYPES = Literal["close", "invalid"]
NOTICE_TYPES = Literal["description", "title"]

DEFAULT_SETTINGS_CHANNEL = {
    "close_tag": None,
    "invalid_tag": None,
    "tag_messages": {},
    "tag_notices": {
        "is_enabled": False,
        "description": "",
        "title": "Tag Notice",
        "hints": {}
    }
}


class ThreadManagement(commands.Cog):
    """
    Manage threads in your server.
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(
            self, identifier=21346578436, force_registration=True)
        self.log = logging.getLogger("red.roxcogs.threadmgmt")
        self.log.setLevel(logging.INFO)
        self.config.register_channel(**DEFAULT_SETTINGS_CHANNEL)

    def _overwrite_view(self, ctx: commands.Context):
        """
        Returns a ConfirmView
        """
        view = views.ConfirmView(ctx.author)
        view.confirm_button.style = discord.ButtonStyle.red
        view.confirm_button.label = "Confirm"
        view.dismiss_button.label = "Cancel"
        return view

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

    @thread_set.group(name="notice")
    async def notice_set(self, ctx: commands.Context):
        """
        Sets options for ThreadManagement notices
        """

    @notice_set.command(name="toggle", aliases=["enable", "on", "disable", "off"])
    @checks.admin_or_permissions(manage_threads=True)
    async def toggle_notice(self, ctx: commands.Context, channel: discord.ForumChannel):
        """
        Toggle tag notices for the mentioned ForumChannel
        """
        config = self.config.channel(channel)
        state = not await config.tag_notices.is_enabled()
        await config.tag_notices.is_enabled.set(state)
        await ctx.send(f"Tag notices are now {'enabled' if state else 'disabled'} for {channel.mention}")

    @notice_set.command(name="hint")
    @checks.admin_or_permissions(manage_threads=True)
    async def set_notice_hint(self, ctx: commands.Context, channel: discord.ForumChannel,
                              tag: str, name: str, *, text: str):
        """
        Set the hint for the tag for the mentioned ForumChannel
        """
        config = self.config.channel(channel)

        if tag == "is_enabled":
            return await ctx.send("You can't set a hint for is_enabled")
        if tag not in [x.name for x in channel.available_tags]:
            return await ctx.send(
                f"{tag} is not a valid tag for {channel.mention}, valid tags are: "
                f"`{', '.join([x.name for x in channel.available_tags])}`"
            )
        if len(text) > 1020:
            return await ctx.send("Text must be 1020 characters or less")
        if len(name) > 250:
            return await ctx.send("Name must be 250 characters or less")

        if await config.get_raw("tag_notices", "hints", tag, default={}) != {}:
            view = self._overwrite_view(ctx)
            view.message = await ctx.send(
                f"There is already a hint set for {tag} in {channel.mention}, "
                f"it is \n```{await config.get_raw('tag_notices', 'hints', tag, 'text')}```\n replace?",
                view=view
            )
            await view.wait()
            await view.message.delete()
            if not view.result:
                return

        await config.tag_notices.hints.set_raw(tag, value={"name": name, "text": text})
        embed = discord.Embed(title="New Tag Hint", description=f"This hint will be a part of a message posted in "
                              f"{channel.mention} when a thread is tagged with {tag}", color=ctx.guild.me.color)
        embed.add_field(name=name, value=text)
        await ctx.send(embed=embed)

    @notice_set.command(name="embed")
    @checks.admin_or_permissions(manage_threads=True)
    async def set_notice_embed(self, ctx: commands.Context, embed_type: NOTICE_TYPES,
                               channel: discord.ForumChannel, *, text: str):
        """
        Set the notice title or desription for the mentioned ForumChannel
        """
        config = await self.config.channel(channel).get_raw("tag_notices", embed_type, default=None)

        maxChar = 250 if embed_type == "title" else 2000
        if len(text) > maxChar:
            return await ctx.send(f"Text must be {maxChar} characters or less")

        if config is not None:
            view = self._overwrite_view(ctx)
            view.message = await ctx.send(
                f"There is already a {embed_type.title()} for {channel.mention}, it is \n```{config}```\n replace?",
                view=view
            )
            await view.wait()
            await view.message.delete()
            if not view.result:
                return
        await ctx.send(f"{embed_type.title()} is now set to ```{text}``` for {channel.mention}")
        await self.config.channel(channel).set_raw("tag_notices", embed_type, value=text)

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
            view = self._overwrite_view(ctx)
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

    async def on_close_tag(self, message: discord.Thread, tag):
        """
        Acts on a thread being tagged as closed
        """
        seconds = 10
        closingAt = discord.utils.utcnow() + timedelta(seconds=seconds)
        closingTxt = discord.utils.format_dt(closingAt, style="R")
        warnMsg = await message.send(
            f"The thread has been tagged as {tag}, and will be closed in {closingTxt} if tag is still present")
        await asyncio.sleep(seconds - 1)
        if tag in [x.name for x in message.parent.get_thread(message.id).applied_tags]:
            await warnMsg.edit(content=f"The thread has been tagged as {tag}, and is closed")
            await message.edit(archived=True, locked=True)
        else:
            await warnMsg.delete()
        return

    async def on_invalid_tag(self, config: Config, message: discord.Thread, tag):
        """
        Sends warning message to the thread when it is tagged as invalid
        """
        warnMsg = await message.send(
            f"The thread has been tagged as {tag} by a human, this likely happened because helpful "
            "information was missing from the post."
        )
        await config.tag_messages.set_raw(message.id, value={"invalid": warnMsg.id})

    async def off_invalid_tag(self, config: Config, message: discord.Thread):
        """
        Removes the warning message from the thread when it is untagged as invalid
        """
        warnMsg = await config.tag_messages.get_raw(message.id, "invalid")
        if warnMsg:
            await (await message.fetch_message(warnMsg)).delete()
            await config.tag_messages.clear_raw(message.id, "invalid")

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        """
        Listen on thread updates to see if we need to do anything.
        """
        if isinstance(before.parent, discord.ForumChannel):
            config = self.config.channel(before.parent)
            closeTag = await config.close_tag()
            invalidTag = await config.invalid_tag()

            if after.archived:
                return await config.tag_messages.clear_raw(before.id)

            newTags = [
                x.name for x in after.applied_tags if x not in before.applied_tags]
            oldTags = [
                x.name for x in before.applied_tags if x not in after.applied_tags]

            if invalidTag in newTags:
                await self.on_invalid_tag(config=config, message=before, tag=invalidTag)
            elif invalidTag in oldTags:
                await self.off_invalid_tag(config=config, message=before)
            if closeTag in newTags:
                await self.on_close_tag(message=before, tag=closeTag)
            return
    ####

    async def do_tag_notice(self, thread: discord.Thread, tag_notices: dict, description: str = None, title: str = None):
        """
        Sends a notice to the thread when it is tagged
        """
        seconds = 3
        waitTxt = discord.utils.format_dt(
            (discord.utils.utcnow() + timedelta(seconds=seconds)), style="R")
        embed = discord.Embed(
            title=title, color=thread.guild.me.color, description=description)
        msg = await thread.send(f"This message will be updated in {waitTxt}, based on the tags applied to this thread",
                                embed=embed)
        await asyncio.sleep(seconds)
        appliedTags = [x.name for x in thread.applied_tags]
        for notice in tag_notices:
            if notice in appliedTags:
                embed.add_field(
                    name=tag_notices[notice]["name"], value=tag_notices[notice]["text"])
        await msg.edit(embed=embed, content=None)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        """
        Listen on thread creation to see if we need to do anything.
        """
        config = self.config.channel(thread.parent)

        if await config.tag_notices.is_enabled():
            await self.do_tag_notice(thread=thread, tag_notices=await config.tag_notices.hints(),
                                     description=await config.tag_notices.description(),
                                     title=await config.tag_notices.title())
