# Bot Packages
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.views import SimpleMenu

import copy
import logging


class Backports(commands.Cog):
    """
    Commands that originates from my other bots.
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.log = logging.getLogger("red.roxcogs.backports")
        self.log.setLevel(logging.INFO)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def oldest(self, ctx):
        """
        Lists the oldest accounts on the server
        """
        formattedString = ""

        members = sorted(ctx.guild.members, key=lambda m: m.created_at)
        for index, member in enumerate(members, start=1):
            user = ctx.guild.get_member(member.id)
            userCreatedDate = int(member.created_at.timestamp())
            createdOn = f"<t:{userCreatedDate}> that is <t:{userCreatedDate}:R>"
            formattedString += f"**#{index}** {user.name}#{user.discriminator} - {createdOn}\n"

        pages = pagify(formattedString, delims=("\n"))
        pages = [{"embed": discord.Embed(description=page, title="Oldest account on the server")} for page in pages]

        if len(pages) == 1:
            await ctx.send(**pages[0])
        else:
            selectMenu = len(pages) >= 5 <= 25
            await SimpleMenu(pages, use_select_menu=selectMenu, use_select_only=selectMenu).start(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def toproles(self, ctx):
        """
        Lists roles in order of the member count
        """

        guildRoles = ctx.guild.roles
        formattedString = ""

        if len(guildRoles) == 1:
            return await ctx.send("This guild only have one role")

        roles = list(sorted(guildRoles, key=lambda role: len(role.members), reverse=True))

        for role in roles:
            if role.name == "@everyone":
                continue
            formattedString += f"{role.mention} - {len(role.members)} - {discord.utils.format_dt(role.created_at)}\n"

        pages = pagify(formattedString, delims=("\n"))
        pages = [{"embed": discord.Embed(description=page,
                                         title="Sorted list of the roles in the guild, by members")} for page in pages]

        if len(pages) == 1:
            await ctx.send(**pages[0])
        else:
            await SimpleMenu(pages, use_select_only=len(pages) >= 5 <= 25).start(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def role(self, ctx, *, role: discord.Role):
        """
        Shows details about a role
        """

        if role.name == "@everyone":
            return await ctx.send("There is no details for `@everyone`")

        if str(role.color) != "#000000":
            color = role.color
        else:
            color = discord.Colour(0x99AAB5)

        hoisted = role.hoist
        mentionable = role.mentionable

        members = []
        pageMembers = False
        for member in role.members:
            members.append(f"{member.name}#{member.discriminator}")
        members = ", ".join(members)

        if len(members) > 1024:
            pageMembers = True
        if len(members) == 0:
            members = "**No Members**"

        permissions = ", ".join([permission for permission, value in iter(role.permissions) if value is True])

        embed = discord.Embed(title=role.name, description=f"{role.mention}\n**ID:** {role.id}", color=color)
        embed.set_author(name=role.guild.name)
        if ctx.guild.icon is not None:
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        embed.add_field(name="Color", value=str(role.color))
        embed.add_field(name="Created", value=discord.utils.format_dt(role.created_at, style="R"))
        embed.add_field(name="Position", value=role.position)
        embed.add_field(name="Mentionable", value=mentionable)
        if role.display_icon:
            embed.set_image(url=role.display_icon.url)
        if role.is_bot_managed():
            embed.add_field(name="Managed by a 3rd party", value=role.is_bot_managed())
        if role.is_integration():
            embed.add_field(name="Integration", value=role.is_integration())
        if role.is_premium_subscriber():
            embed.add_field(name="Boost-role", value=role.is_premium_subscriber())
        embed.add_field(name="Hoisted", value=hoisted)
        if permissions:
            embed.add_field(name="Permissions", value=permissions, inline=False)
        embed.add_field(name=f"Users with the role({len(role.members)})", value=members, inline=False)
        if not pageMembers:

            await ctx.send(embed=embed)
        elif pageMembers:

            pages = pagify(members, delims=(", ",), page_length=1000)
            pages = list(pages)
            theField = len(embed.fields)
            selectObject = []
            for ind, page in enumerate(pages):
                pagedEmbed = discord.Embed.from_dict(copy.deepcopy(embed.to_dict()))
                pagedEmbed.remove_field(theField - 1)
                pagedEmbed.add_field(
                    name=f"Users with the role({len(role.members)})", value=page.strip(", "), inline=False)
                pagedEmbed.set_footer(text=f"Page {ind + 1} of {len(pages)}")
                selectObject.append({"embed": pagedEmbed})
            await SimpleMenu(selectObject).start(ctx)
