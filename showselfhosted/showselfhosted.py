# Bot Packages
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red

import logging
import random
from types import MappingProxyType
from typing import Any, Dict, Literal, Union, get_args

DEFAULT_SETTINGS = {
    "episode_feed_announce_channel": None,
    "episode_feed_announce_role": None,
    "episode_feed_announce": False,
    "episode_feed_forum_channel": None,
    "episode_feed_forum": False,
    "episode_feed_name": None,
    "fuckfeed": None,
}

BOOL_TYPES = Literal["announce", "forum"]
CHANNEL_TYPES = Literal["announce", "forum"]
ROLE_TYPES = Literal["announce"]
TRUE_VALUES = Literal["true", "yes", "enable", "enabled"]
FALSE_VALUES = Literal["false", "no", "disable", "disabled"]
BOOL_VALUES = Literal[TRUE_VALUES, FALSE_VALUES]


class ShowSelfHosted(commands.Cog):
    """
    Specialised functions for the Self-Hosted server
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=78954872478, force_registration=True)
        self.log = logging.getLogger("red.roxcogs.showselfhosted")
        self.log.setLevel(logging.INFO)
        self.config.register_guild(**DEFAULT_SETTINGS)

    @commands.group(name="showselfhosted", aliases=["ssh"])
    @checks.admin_or_permissions(manage_threads=True)
    async def ssh_group(self, ctx: commands.Context):
        """
        Options for ShowSelfHosted
        """

    @ssh_group.command(name="channel")
    async def ssh_channels(self, ctx: commands.Context, channel_type: CHANNEL_TYPES,
                           channel: Union[discord.TextChannel, discord.ForumChannel]):
        """
        Set channels for ShowSelfHosted feeds
        """
        await self.config.guild(ctx.guild).set_raw(f"episode_feed_{channel_type}_channel", value=channel.id)
        await ctx.send(f"Set {channel_type} channel to {channel.mention}")

    @ssh_group.command(name="role")
    async def ssh_roles(self, ctx: commands.Context, role_type: ROLE_TYPES, role: discord.Role):
        """
        Set roles for ShowSelfHosted feeds
        """
        await self.config.guild(ctx.guild).set_raw(f"episode_feed_{role_type}_role", value=role.id)
        await ctx.send(f"Set {role_type} role to {role.mention}", allowed_mentions=discord.AllowedMentions.none())

    @ssh_group.command(name="name")
    async def ssh_name(self, ctx: commands.Context, *, name: str):
        """
        Set name for ShowSelfHosted feed
        """
        await self.config.guild(ctx.guild).episode_feed_name.set(name)
        await ctx.send(f"Set rss feed name to {name}")

    @ssh_group.command(name="set")
    async def ssh_bool(self, ctx: commands.Context, bool_type: BOOL_TYPES, bool_value: BOOL_VALUES):
        """
        Set status for ShowSelfHosted feeds
        """
        if bool_value in get_args(TRUE_VALUES):
            bool_value = True
        elif bool_value in get_args(FALSE_VALUES):
            bool_value = False
        else:
            return await ctx.send("Invalid value")
        await self.config.guild(ctx.guild).set_raw(f"episode_feed_{bool_type}", value=bool_value)
        await ctx.send(f"Set {bool_type} to {bool_value}")

    @commands.Cog.listener()
    async def on_aikaternacogs_rss_message(
            self, *, channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel],
            feed_data: Dict[str, Any], feedparser_dict: MappingProxyType[str, Any], force: bool, **_kwargs: Any):
        """
        Listen for RSS events and create a thread

        Listener documentation:
        https://github.com/aikaterna/aikaterna-cogs/blob/fb6a65e00bfbe9a3935967cde1da343214a28a2f/rss/rss.py#L1515-L1530
        """
        feedName = feed_data["name"]

        config = self.config.guild(channel.guild)

        epLink = feedparser_dict["link"]
        epTitle = feedparser_dict["title"]

        if feedName == await config.episode_feed_name():
            if await config.episode_feed_forum() is True:
                if await config.episode_feed_forum_channel() is None:
                    return
                forumId = await config.episode_feed_forum_channel()
                forumChannel = channel.guild.get_channel(forumId)
                post = await forumChannel.create_thread(name=epTitle, content=epLink)

                if await config.episode_feed_announce():
                    try:
                        announceChannel = channel.guild.get_channel(await config.episode_feed_announce_channel())
                        announceRole = channel.guild.get_role(await config.episode_feed_announce_role())
                    except Exception as e:
                        print(e)
                        return
                    announceTextCandidate = [
                        "Hey {Role}, a new episode has been [released]({Link})!\n\nDiscuss here > {Post}",
                        "Meep morp\n\nSpotted a new episode on [the interwebs]({Post})\nCalling all {Role} detectives to investigate in {Post}",
                        "# 📻 {Role}\n## 🌐 {Link} \n### 🧵 {Post}"
                    ]
                    announceText = random.choice(announceTextCandidate).format(
                        Role=announceRole.mention, Link=epLink, Post=post.thread.jump_url)

                    await announceChannel.send(announceText)
