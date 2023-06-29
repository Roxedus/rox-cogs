# Bot Packages
import discord
from redbot.core import Config, app_commands, checks, commands
from redbot.core.bot import Red

import asyncio
import datetime
import logging
import re
import traceback

TIMEDELTA_REGEX = (r'((?P<days>-?\d+)d)?'
                   r'((?P<hours>-?\d+)h)?'
                   r'((?P<minutes>-?\d+)m)?'
                   r'((?P<seconds>-?\d+)s)?')
TIMEDELTA_PATTERN = re.compile(TIMEDELTA_REGEX, re.IGNORECASE)

DEFAULT_SETTINGS = {
    "create_forum_post": None,
    "temp_dump": {},
    "temp_forum": 0,
    "temp_role": 0,
}

DEFAULT_SETTINGS_CHANNEL = {
    "create_forum_post": None,
    "last_title": "",
    "last_content": "",
}

send_overwrite = discord.PermissionOverwrite()
send_overwrite.send_messages = True
send_overwrite.send_messages_in_threads = True
send_overwrite.view_channel = True
send_overwrite.read_messages = True


class TempChannel(commands.Cog):
    """
    Functions for the temporary channels
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=785646342, force_registration=True)
        self.log = logging.getLogger("red.roxcogs.tempchannel")
        self.log.setLevel(logging.INFO)
        self.config.register_guild(**DEFAULT_SETTINGS)
        self.config.register_channel(**DEFAULT_SETTINGS_CHANNEL)

    async def cog_unload(self) -> None:
        for task in await self._get_all_my_tasks():
            self.log.debug("Canceling task %s due to cog unload", task.get_name())
            task.cancel()

    async def _get_all_my_tasks(self) -> set[asyncio.Task]:
        """
        Get tasks created by this cog
        """
        _ret = set()
        for task in asyncio.all_tasks():
            if task.get_name().startswith("tempchannel-"):
                _ret.add(task)
        return _ret

    async def _get_all_guild_tasks(self, guild: discord.Guild) -> set[asyncio.Task]:
        """
        Get tasks created for this guild
        """
        _ret = set()
        for task in await self._get_all_my_tasks():
            cog, action, guildId, channelId = task.get_name().split("-")
            if int(guildId) == guild.id:
                _ret.add(task)
        return _ret

    async def _get_channel_task(self, channel: discord.TextChannel) -> asyncio.Task:
        """
        Get tasks created for the specified channel
        """
        for task in await self._get_all_my_tasks():
            cog, action, guildId, channelId = task.get_name().split("-")
            if int(channelId) == channel.id:
                return task
        return None

    async def _task_wait_until(self, until: datetime.datetime) -> None:
        """
        Schedules a task to wait until the specified datetime
        """
        now = datetime.datetime.utcnow()
        seconds = (until - now).total_seconds()
        await asyncio.sleep(seconds)

    async def _close_channel(self, close_msg: discord.Message, thread: discord.Thread = False) -> None:
        """
        Removes the overwritten permissions
        """
        role = await self.config.guild(close_msg.guild).temp_role()
        target = close_msg.guild.get_role(role)

        msgPrefix = ""
        if thread:
            msgPrefix = f", and a thread has been opened {thread.thread.mention} "

        self.log.debug("Removing override for %s in %s", target.name, close_msg.channel.name)
        await close_msg.channel.set_permissions(target, overwrite=None)
        await close_msg.edit(content=f"This channel is now closed{msgPrefix}")
        await close_msg.unpin()

    async def _open_channel(self, close_msg: discord.Message) -> None:
        """
        Sets an overwrite to allow the role to send messages
        """
        role = await self.config.guild(close_msg.guild).temp_role()
        target = close_msg.guild.get_role(role)

        self.log.debug("Overriding %s in %s", target.name, close_msg.channel.name)
        await close_msg.channel.set_permissions(target, overwrite=send_overwrite)

    async def closing_task(self, until: datetime.datetime, close_msg: discord.Message, forum_dict: dict = None) -> None:
        """
        Task to handle the closing of the channel
        """
        thread = None
        try:
            self.log.debug("Starting open-loop in %s", close_msg.channel.name)
            await self._open_channel(close_msg=close_msg)
            await self._task_wait_until(until)
            self.log.debug("Done waiting in %s, closing", close_msg.channel.name)
            if forum_dict:
                if forum_dict.get("content"):
                    forum_dict["content"] += f"\n\nChatter prior to closing: {close_msg.jump_url}"
                self.log.debug("Creating thread in %s", close_msg.channel.name)
                forumId = await self.config.guild(close_msg.guild).temp_forum()
                forum = close_msg.guild.get_channel_or_thread(forumId)
                thread = await forum.create_thread(**forum_dict)
            await self._close_channel(close_msg=close_msg, thread=thread)

        except asyncio.CancelledError:
            self.log.debug("Task cancelled for %s", close_msg.channel.name)
            await self._close_channel(close_msg=close_msg)

    async def parse_delta(self, human: str) -> str:  # gist.github.com/santiagobasulto/698f0ff660968200f873a2f9d1c4113c
        """ Parses a human readable timedelta (3d5h19m) into a datetime.timedelta.
        Delta includes:
        * Xd days
        * Xh hours
        * Xm minutes
        * Xs seconds
        Values can be negative following timedelta's rules. Eg: -5h-30m
        """
        match = TIMEDELTA_PATTERN.match(human)
        if match:
            parts = {k: int(v) for k, v in match.groupdict().items() if v}
            return datetime.timedelta(**parts)
        return None

    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="tset")
    async def _timed_set(self, ctx: commands.Context) -> None:
        """
        Commands to manage setttings for temporary writeable channels
        """

    @_timed_set.group(name="default")
    async def _timed_set_default(self, ctx: commands.Context) -> None:
        """
        Commands to manage default setttings for temporary writeable channels
        """

    @_timed_set_default.command(name="forum")
    async def _timed_set_default_forum(self, ctx: commands.Context, state: bool = None,
                                       channel: discord.TextChannel = None) -> None:
        """
        Sets the default behaviour for the creation of forum threads on closing a channel.
        Toggles if no state is given
        """

        msgPostfix = ""

        if channel:
            config = self.config.channel(channel)
            msgPostfix = f" for {channel.mention}"
        else:
            config = self.config.guild(ctx.guild)
        if state is None:
            state = not await config.create_forum_post()
        if not isinstance(state, bool):
            return await ctx.send(f"{state} is not a boolean")
        await config.create_forum_post.set(state)
        await ctx.send(f"Forum post creation on channel close set to {state}{msgPostfix}")

    @_timed_set.command(name="forum")
    async def _timed_set_forum(self, ctx: commands.Context, forum: discord.ForumChannel) -> None:
        """
        Sets the forum channel to use for the creation of threads on closing a channel
        """
        config = self.config.guild(ctx.guild)
        if not isinstance(forum, discord.ForumChannel):
            return await ctx.send(f"{forum} is not a forum channel")
        await config.temp_forum.set(forum.id)
        await ctx.send(f"Forum post creation set to {forum.mention}")

    @_timed_set.command(name="role")
    async def _timed_set_role(self, ctx: commands.Context, role: discord.Role) -> None:
        """
        Sets the role to change permissions for on closing a channel
        """
        config = self.config.guild(ctx.guild)
        if not isinstance(role, discord.Role):
            return await ctx.send(f"{role} is not a role")
        await config.temp_role.set(role.id)
        await ctx.send(f"Changing {role.mention} on channel opening")

    _timed = app_commands.Group(name="timed", description="Commands to manage temporary writeable channels")

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(start_time="Relative time to hold the channel open(1d2h3m4s).")
    @app_commands.describe(start_time="Start time")
    @_timed.command(name="open")
    async def t_open(self, interaction: discord.Interaction, start_time: str = "s300", channel: discord.TextChannel = None) -> None:
        """
        Command to temporarily open the channel for a specified amount of time
        """

        channel = channel or interaction.channel

        if await self._get_channel_task(channel):
            return await interaction.response.send_message(f"{channel.name} is already scheduled to close")

        config = self.config.guild(interaction.guild)
        channelConfig = self.config.channel(channel)
        notSetup = {"required": [], "optional": []}
        _role = interaction.guild.get_role(await config.temp_role())
        _forum = interaction.guild.get_channel(await config.temp_forum())
        _lastTitle = await channelConfig.last_title()
        _lastContent = await channelConfig.last_content()
        if _lastTitle:
            m = re.search(r'\d+$', _lastTitle)
            if m is not None:
                _lastTitle = _lastTitle.replace(m.group(), str(int(m.group()) + 1))
        if _lastContent:
            m = re.search(r'\d+$', _lastContent)
            if m is not None:
                _lastContent = _lastContent.replace(m.group(), str(int(m.group()) + 1))

        _doForum = await channelConfig.create_forum_post() or await config.create_forum_post()

        if not isinstance(_role, discord.Role):
            notSetup["required"].append("role")
        if not isinstance(_forum, discord.ForumChannel):
            notSetup["optional"].append("forum")
        if notSetup["required"]:
            return await interaction.response.send_message(f"The following settings are not set up: \
                                                           {', '.join(notSetup['required'])}",
                                                           ephemeral=True)

        human = await self.parse_delta(start_time)
        if not human:
            return await interaction.response.send_message("Invalid time format", ephemeral=True)
        view_data = {"name": _lastTitle, "content": _lastContent}
        view = OpenThread(_forum, view_data, _doForum)
        await interaction.response.send_message(content="Do you want to continue?", view=view, ephemeral=True)
        await view.wait()
        if not view.post:
            return await interaction.edit_original_response(content="Opening of channel cancelled")

        closingAt = datetime.datetime.utcnow() + human
        closeMsg = await channel.send(
            content=f"{channel.name} is now scheduled to close at {discord.utils.format_dt(closingAt, style='t')}")

        _forumDict = view.view_data if _doForum or view.do_forum else None

        if _forumDict.get("name") and _forumDict.get("content"):
            try:
                len(_forumDict["name"]) <= 100
                len(_forumDict["content"]) <= 1900
            except TypeError:
                _forumDict = None
            except AttributeError:
                _forumDict = None
        else:
            _forumDict = None

        if _forumDict:
            await channelConfig.last_title.set(_forumDict.get("name"))
            await channelConfig.last_content.set(_forumDict.get("content"))
        self.bot.loop.create_task(self.closing_task(until=closingAt, close_msg=closeMsg, forum_dict=_forumDict),
                                  name=f"tempchannel-CloseChannel-{closeMsg.guild.id}-{closeMsg.channel.id}")

        return await interaction.edit_original_response(content="Channel scheduled to close", embed=None, view=None)


class _SetForumButton(discord.ui.Button):
    def __init__(self, view_data: dict, forum) -> discord.ui.Button:
        _forumStyle = discord.ButtonStyle.primary if forum else discord.ButtonStyle.secondary
        _forumLabel = "Set forum" if forum else "Set forum(forum channel not set up)"
        self.view_data = view_data
        super().__init__(style=_forumStyle, label=_forumLabel, custom_id="forum", row=0, disabled=not forum)

    async def callback(self, interaction: discord.Interaction):
        _modal = ForumModal(view_data=self.view_data)
        await interaction.response.send_modal(_modal)
        await _modal.wait()
        await interaction.edit_original_response(content="Forum post will be created with this data",
                                                 view=self.view)


class _DoForumButton(discord.ui.Button):
    """
    Dynamic button to toggle forum post creation
    """

    def __init__(self, do_forum) -> discord.ui.Button:
        _forumStyle = discord.ButtonStyle.success if do_forum else discord.ButtonStyle.red
        _forumEmoji = "✔" if do_forum else "❌"
        _forumLabel = "Post forum"
        super().__init__(style=_forumStyle, label=_forumLabel, emoji=_forumEmoji, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.do_forum = not self.view.do_forum
        self.emoji = "✔" if self.view.do_forum else "❌"
        self.style = discord.ButtonStyle.success if self.view.do_forum else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self.view)


class ForumModal(discord.ui.Modal):
    """
    Modal used to gather information for the forum post
    """

    def __init__(self, view_data: dict):
        self.view_data = view_data
        super().__init__(title="Create Forum post on close", timeout=180)
        _name = self.view_data.get("name")
        _content = self.view_data.get("content")

        self.add_item(
            discord.ui.TextInput(label="Title for Forum post", custom_id="name", default=_name,
                                 max_length=100, min_length=1))
        self.add_item(
            discord.ui.TextInput(label="Description for Forum post", custom_id="content", default=_content,
                                 max_length=1900, min_length=1))

    async def on_submit(self, interaction: discord.Interaction):
        self.view_data.update({x.custom_id: x.value for x in self.children})
        # await interaction.response.defer()
        embed = discord.Embed(title="Title: " + self.view_data.get("name"),
                              description="Description: " + self.view_data.get("content"))
        await interaction.response.edit_message(embed=embed)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.edit_message(content="Oops! Something went wrong.", view=None, embed=None)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)


class OpenThread(discord.ui.View):
    def __init__(self, forum, view_data: dict, do_forum: bool = False) -> discord.ui.View:
        super().__init__()
        self.post = None
        self.do_forum = do_forum
        self.view_data = view_data
        self.add_item(_SetForumButton(view_data=self.view_data, forum=forum))
        if forum:
            self.add_item(_DoForumButton(do_forum=self.do_forum))

    @discord.ui.button(label='Open', style=discord.ButtonStyle.green, row=0)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Opening...", view=None)
        self.post = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, row=0)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelling...", view=None)
        self.post = False
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.edit_message(content="Oops! Something went wrong.", view=None, embed=None)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)
