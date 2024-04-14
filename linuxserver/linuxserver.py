# Bot Packages
import discord
from redbot.core import Config, checks, commands, app_commands
from redbot.core.bot import Red
from redbot.core.utils import views

import asyncio
import logging
from typing import Literal, Mapping, Optional

from .ghapi import GitHubAPI

SETTING_TYPES = Literal["org_name", "repo_prefix"]

DEFAULT_SETTINGS_GUILD = {
    "githubcards": [],
    "org_name": None,
    "repo_prefix": None,
}


class LinuxServer(commands.Cog):
    """
    Manages common tasks for the LinuxServer.io Discord server
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self._ready = asyncio.Event()
        self.config = Config.get_conf(self, identifier=456783465256, force_registration=True)
        self.log = logging.getLogger("red.roxcogs.linuxserver")
        self.log.setLevel(logging.INFO)
        self.ghapi: GitHubAPI = None
        self.config.register_guild(**DEFAULT_SETTINGS_GUILD)
        self.ctx_support = app_commands.ContextMenu(
            name='Get Support',
            callback=self.support_context,
        )
        self.bot.tree.add_command(self.ctx_support)

    # Gotten from https://github.com/Kowlin/Sentinel/blob/8040f09ed5cd51aaa7ccdd7d8711e2dcc664283f/githubcards/core.py#L84-L92
    async def _get_token(self, api_tokens: Optional[Mapping[str, str]] = None) -> str:
        """Get GitHub token."""
        if api_tokens is None:
            api_tokens = await self.bot.get_shared_api_tokens("github")

        token = api_tokens.get("token", "")
        if not token:
            self.log.error("No valid token found")
        return token

    async def initialize(self):
        """ cache preloading """
        await self._create_client()
        self._ready.set()

    async def _create_client(self) -> None:
        """Create GitHub API client."""
        self.ghapi = GitHubAPI(token=await self._get_token())

    async def _is_setup(self, config: Config) -> Optional[str]:
        setupMsg = []

        if not await config.org_name():
            setupMsg.append("No organisation name set. Please set one with `[p]linuxserver set org <orgname>`")
        if not await config.repo_prefix():
            setupMsg.append("No repo prefix set. Please set one with `[p]linuxserver set repo <reponame>`")
        if not await self._get_token():
            setupMsg.append("No GitHub token set. Please set one with `[p]set api github token <token>`")

        if setupMsg:
            return "\n".join(setupMsg)
        return None

    async def cog_unload(self):
        self.bot.loop.create_task(self.ghapi.session.close())
        self.bot.tree.remove_command(self.ctx_support.name, type=self.ctx_support.type)

    async def _create_support_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="LinuxServer.io Support",
            description="\nPlease could you provide the following information so we can help with supporting your issue:\n"
                        "- Output of `uname -mr && docker version`\n"
                        "- Output of `cat /etc/os-release`\n"
                        "- Docker run command or compose snippet\n"
                        "- Container logs beginning with our logo (<#805732277501034506> 5)\n"
                        "- Describe the issue you're having with the container.\n"
                        "\n\nMind the <#805732277501034506> and our [Support Policy](https://www.linuxserver.io/supportpolicy) "
                        "and remember this server supports the containers, not the apps inside (they have their own support)."
                        "\n\n```diff\n- Failure to provide logs and compose/run might delay a response\n```",
            color=discord.Color.blurple()
        )
        return embed

    @commands.group(name="linuxserver", aliases=["lsio"])
    @checks.admin_or_permissions(manage_messages=True)
    async def lsio_group(self, ctx: commands.Context):
        """
        Options for LinuxServer.io
        """

    @lsio_group.command(name="set")
    async def lsio_set(self, ctx: commands.Context, setting: SETTING_TYPES, value: str):
        """
        Set the settings for LinuxServer.io
        """
        config = self.config.guild(ctx.guild)
        await config.set_raw(setting, value=value)
        await ctx.send(f"Set {setting} to {value}")

    @lsio_group.group(name="githubcards", aliases=["ghc"])
    async def lsio_ghc_group(self, ctx: commands.Context):
        """
        Options for GitHub Cards
        """

    @lsio_ghc_group.command(name="add")
    async def lsio_ghc_add(self, ctx: commands.Context, container: str):
        """
        Add a GitHub card
        """
        container = container.lower()
        config = self.config.guild(ctx.guild)

        isSetup = await self._is_setup(config)

        if isinstance(isSetup, str):
            embed = discord.Embed(title="GitHub Cards", description=isSetup)
            await ctx.send(embed=embed)
            return

        owner = await config.org_name()
        repoPrefix = await config.repo_prefix()
        cards = await config.githubcards()

        repo = repoPrefix + container

        if f"{owner}/{repo}" in cards:
            return await ctx.send("Prefix already managed by this cog")
        if not await self.ghapi.verify_repo(owner, repo):
            return await ctx.send("Repo not found")

        self.bot.dispatch("kowlin_ghc_add", guild=ctx.guild, owner=owner, repo=repo, prefix=container)
        cards.append(f"{owner}/{repo}")
        await config.githubcards.set(cards)

        await ctx.send(f"Added {owner}/{repo} with prefix {container}")

    @lsio_ghc_group.command(name="sync")
    async def lsio_ghc_sync(self, ctx: commands.Context):
        """
        Syncs GitHub cards from a GitHub organisation
        """
        config = self.config.guild(ctx.guild)

        isSetup = await self._is_setup(config)

        if isinstance(isSetup, str):
            embed = discord.Embed(title="GitHub Cards", description=isSetup)
            await ctx.send(embed=embed)
            return

        orgName = await config.org_name()
        prefix = await config.repo_prefix()
        cards = await config.githubcards()

        view = views.ConfirmView(ctx.author)
        view.confirm_button.style = discord.ButtonStyle.red
        view.confirm_button.label = "Yes"
        view.dismiss_button.label = "Cancel"
        view.message = await ctx.send(
            "This is a api-heavy action, as it fetches all public repos from a organization. "
            "Are you sure you want to continue?",
            view=view
        )
        await view.wait()
        if view.result:
            pass
        else:
            await ctx.send("Cancelled", delete_after=10)
            return

        await ctx.typing()
        newRepos = []
        repos = await self.ghapi.get_repos("orgs", orgName)
        allRepos = [repo["full_name"]
                    for repo in repos if repo["name"].startswith(prefix) and not repo["archived"]]
        filteredRepos = [repo for repo in allRepos if repo not in cards]
        if filteredRepos == []:
            await view.message.edit(content="No new repos found", view=None)
            return

        for i in filteredRepos:
            owner, repo = i.split("/")
            self.bot.dispatch(
                "kowlin_ghc_add",
                guild=ctx.guild,
                owner=owner,
                repo=repo,
                prefix=repo.replace(prefix, ""),
            )
            cards.append(i)
            newRepos.append(repo)
            await asyncio.sleep(1)

        await config.githubcards.set(cards)
        embed = discord.Embed(title="GitHub Cards", description=f"Added `{', '.join(newRepos)}`")
        await view.message.edit(content=f"Added {len(newRepos)} new repos", embed=embed, view=None)

    @commands.command(name="support", aliases=["logs", "compose"])
    async def support(self, ctx: commands.Context, user: discord.Member = None) -> None:
        """
        Get support from LinuxServer.io
        """
        await ctx.message.delete()
        await ctx.send(
            f"{ctx.author.mention} please provide some information" if user else None,
            embed=await self._create_support_embed(),
            )

    @app_commands.command(name="support")
    @app_commands.guild_only()
    async def support_slash(self, interaction: discord.Interaction, user: discord.Member = None) -> None:
        await interaction.response.send_message("Support instructions are sent", ephemeral=True)
        return await interaction.channel.send(
            f"{user.mention} please provide some information" if user else None,
            embed=await self._create_support_embed()
            )

    @app_commands.guild_only()
    async def support_context(self, interaction: discord.Interaction, message: discord.Message) -> None:
        await interaction.response.send_message("Support instructions are sent", ephemeral=True)
        return await message.reply(
            embed=await self._create_support_embed(), mention_author=True
            )