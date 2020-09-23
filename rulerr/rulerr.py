# Bot Packages
import discord
from discord import embeds
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n

import asyncio
import logging
import re
from typing import Union

from .helpers import RuleHelper
from .manager import RuleManager

_ = Translator('Rulerr', __file__)


@cog_i18n(_)
class Rulerr(commands.Cog):
    """Cog to manage laws with rules"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9783465975)
        default_settings = {
            "auto_update": [],
            "channel": {},
            "default_rule": None,
            "react_rules": [],
            "rule_prefix": "§",
            "rules": {},
            "interface_lang": "en_en",
            "emoji": "\N{INCOMING ENVELOPE}"
        }
        self.log = logging.getLogger("red.roxcogs.rulerr")
        self.log.setLevel(logging.INFO)
        self.config.register_guild(**default_settings)
        self.helper = RuleHelper(bot)

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

    @commands.guild_only()
    @commands.command(name="rule")
    async def rules(self, ctx, law: Union[int, str] = None, *, num: str = None):
        """Command to explicit get the rules in a law"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)

        if isinstance(law, int):
            if num is None:
                num = str(law)
            else:
                num = str(law) + " " + num
            law = await rules.get_settings("default_rule")

        rule_text, date = await rules.get_rule_text(law)

        formated = await rules.get_rules_formatted()

        if not formated:
            return await ctx.send(_('There is currently no laws set up'))

        if rule_text is None:
            return await ctx.send("**{_txt}:**\n{_list}".format(_txt=_('Lists all laws for this guild'),
                                                                _list=formated))

        if rule_text == "":
            return await ctx.send(_('This law is completely empty'))

        # # Get only specified rules
        if num is not None:
            await ctx.message.delete()
            partial_rules = ""

            no_dupes = await rules.remove_duplicates(num.split())

            for rule in no_dupes:
                ruleregex = r"(§ *" + re.escape(rule) + r"[a-z]?: [\S ]*)"
                m = re.search(ruleregex, rule_text)
                if m is not None:
                    partial_rules += m.groups()[0] + "\n"

            if partial_rules == "":
                await ctx.send(_('Could not find the rule you were looking for'))
            elif law != await rules.get_settings("default_rule"):
                ctx.send("**{_txt} {law}**\n".format(_txt=_('The rules for the law'), law=law) + partial_rules)
            else:
                await ctx.send(embed=await self.helper._create_embed(partial_rules, date))
        else:
            await ctx.send(embed=await self.helper._create_embed(rule_text, date))

    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="laws")
    async def _rule_settings(self, ctx):
        """Commands for managing rules and laws"""

    @_rule_settings.command(name="new")
    async def newrules(self, ctx, law, *, newrule: str = None):
        """Create a new law, with rules"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        added = await rules.add_rule(law, newrule)
        new_rule = await config.rules.get_raw(law)

        title = (_('The law {law} already exists') if not added else _('Law {law} added')).format(law=law)

        description = _('RuleText') + f':\n```diff\n{new_rule["rule_text"][:980]}\n```'
        if new_rule.get('alternate'):
            description += "\n" + _('AltText') + f':\n```diff\n{new_rule["alternate"][:980]}\n```'

        embed = discord.Embed(title=title, colour=ctx.me.colour)
        embed.description = description
        embed.add_field(name=_('Edited at'), value=new_rule['edited'].split(".")[0])
        await ctx.send(embed=embed)

    @ _rule_settings.command(name="plaintext")
    async def plaintext(self, ctx, law):
        """Sends the law in plaintext"""

        try:
            rule_text = await self.config.guild(ctx.guild).rules.get_raw(law)
            await ctx.send("```\n" + rule_text['rule_text'] + "\n```")
        except KeyError:
            await ctx.send(_('Please ensure {law} is a valid rule').format(law=law))

    @ _rule_settings.command(name="remove")
    async def removerules(self, ctx, law):
        """Removes the law"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        await self.helper._remove_reactions(ctx, rules, law)
        try:
            await rules.remove_rule(law)
            await ctx.send(_('Law removed'))
        except KeyError:
            await ctx.send(_('This law does not exist'))

    @ _rule_settings.command(name="update")
    async def updaterules(self, ctx, law, *, newrule):
        """Updates the law"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        try:
            await rules.edit_rule(law, newrule)
            await self.helper._update_messages(ctx, rules)
        except KeyError:
            await ctx.send(_('Could not find this law'))

    @ _rule_settings.command(name="default")
    async def set_default_rule(self, ctx, law):
        """Set the default law for this guild"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        rule_text, date = await rules.get_rule_text(law)

        if rule_text is None:
            return await ctx.send(
                '{_not}.\n\n**{_these}**:\n{_formated}'.format(
                    _not=_('This law is not in the lawbook'),
                    _these=_('The following laws are in the lawbook'),
                    _formated=await rules.get_rules_formatted()
                )
            )
        await rules.change_setting("default_rule", law.lower())
        await ctx.send(_('{law} is now the default law').format(law=law))

    @ commands.guild_only()
    @ commands.has_permissions(manage_messages=True)
    @ commands.group(name="autoset")
    async def _auto_settings(self, ctx):
        """Commands for setting up automatically message updating"""

    @ _auto_settings.command(name="post")
    async def postauto(self, ctx, law):
        """Sends a message that automatically updates when the law updates"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        rule_text, date = await rules.get_rule_text(law)

        if rule_text is None:
            return await ctx.send(
                '{_not}.\n\n**{_these}**:\n{_formated}'.format(
                    _not=_('This law is not in the lawbook'),
                    _these=_('The following laws are in the lawbook'),
                    _formated=await rules.get_rules_formatted()
                )
            )

        if rule_text == "":
            await ctx.send(_('This law is completly empty'))
            return

        embed = await self.helper._create_embed(rule_text, date)
        msg = await ctx.send(embed=embed)
        await rules.add_link_setting('auto_update', law, await self.helper._format_message_link(msg))

        conf_msg = await ctx.send(_('The message now updates automatically'))
        await asyncio.sleep(5)
        await conf_msg.delete()

    @ _auto_settings.command(name="remove")
    async def remove_auto(self, ctx, link):
        """Remove a message from the list of messages that automatically updates"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        removed = await rules.remove_link_setting("auto_update", "link", link)
        if removed:
            await ctx.send(_('Message removed from list'))
        else:
            await ctx.send(_('Ensure the link is used with {list_command}').format(
                list_command=f'`{ctx.prefix}autoset list`'))

    @ _auto_settings.command(name="add")
    async def autorules(self, ctx, law, link):
        """Adds a old message from the bot to the list of automatically updated messages"""

        msg = await self.helper._get_linked_message(ctx, link)
        if msg is None:
            return await ctx.send(_('Could not find the message'))
        if msg.author != self.bot.user:
            return await ctx.send(_('This only works on messages owned by the bot'))

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        added = await rules.add_link_setting('auto_update', law, await self.helper._format_message_link(msg))

        if added == -1:
            await ctx.send(_('Message already set to automatically update'))
        elif added:
            await ctx.send(_('Message now set to automatically update'))
        else:
            await ctx.send(_('This law does not exist'))

        await self.helper._update_messages(ctx, rules, name=law)

    @ _auto_settings.command(name="list")
    async def _auto_list(self, ctx):
        """Sends a list of the messages set up to automatically update"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        auto_update_messages = await rules.get_settings('auto_update')

        if len(auto_update_messages) == 0:
            return await ctx.send(_('No message is currently set up for automatic updates'))

        embed = await self.helper._create_embed()
        embed.title = '**{}:**'.format(_('Messages set to automatically update'))

        for message in auto_update_messages:
            embed.add_field(name=f'Lov: {message["name"]}', inline=False,
                            value=f'{ctx.guild.get_channel(message["channel"]).mention} [Link]({message["link"]})')

        await ctx.send(embed=embed)

    @ _auto_settings.command(name="fix")
    async def fixauto(self, ctx):
        """Forces a update for automatic messages"""

        rules = RuleManager(self.config.guild(ctx.guild))
        await self.helper._update_messages(ctx, rules)

    @ commands.guild_only()
    @ commands.has_permissions(manage_messages=True)
    @ commands.group(name="reactset")
    async def _react_settings(self, ctx):
        """Commands for setting up alternate rules to DMs triggered by reactions"""

    @ _react_settings.command(name="update")
    async def edit_alternate(self, ctx, law, *, newrule):
        """Update the law with a alternate version"""

        rules = RuleManager(self.config.guild(ctx.guild))
        try:
            await rules.edit_rule(law, newrule, alternate=True)
            await ctx.send(_('Alternate law updated'))
        except KeyError:
            await ctx.send(_('Could not find this law'))

    @ _react_settings.command(name="remove")
    async def remove_alternate(self, ctx, law):
        """Removes the alternate law attatched to the law"""

        rules = RuleManager(self.config.guild(ctx.guild))
        try:
            await rules.remove_rule(law, alternate=True)
            await ctx.send(_('Alternate law removed'))
        except KeyError:
            await ctx.send(_('Could not find this law'))

    @ _react_settings.command(name="list")
    async def show_alternate(self, ctx, law: str = None):
        """Lists the alternate laws attatched to the law"""

        rules = RuleManager(self.config.guild(ctx.guild))
        rule_text, date = await rules.get_rule_text(law, alternate=True)
        if rule_text is not None:
            await ctx.send("```\n" + rule_text + "\n```")
        else:
            return await ctx.send("**{_txt}:**\n{_list}".format(_txt=_('Lists all alternate laws for this guild'),
                                                                _list=await rules.get_rules_formatted(alternate=True)))

    @ _react_settings.command(name="auto_list")
    async def _react_list(self, ctx):
        """Lists the alternate laws set up with reactions"""

        rules = RuleManager(self.config.guild(ctx.guild))
        react_messages = await rules.get_settings('react_rules')

        list_message = '**{}:**\n'.format(_('Reaction-messages set to automatically update'))

        if len(react_messages) == 0:
            return await ctx.send(_('No reaction-message is currently set up for automatic updates'))

        for message in react_messages:
            list_message += f'{message["name"]}: {message["link"]}\n'

        await ctx.send(list_message)

    @ _react_settings.command(name="link")
    async def link_alternate(self, ctx, law, link):
        """Adds a old message from the bot to the list of automatically updated react-messages"""

        msg = await self.helper._get_linked_message(ctx, link)
        if msg is None:
            return await ctx.send(_('Could not find the message'))
        if msg.author != self.bot.user:
            return await ctx.send(_('This only works on messages owned by the bot'))

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        added = await rules.add_link_setting('react_rules', law, await self.helper._format_message_link(msg))

        if added == -1:
            await ctx.send(_('Message already set to automatically update'))
        elif added:
            try:
                await msg.clear_reactions()
                await asyncio.sleep(1)
                await msg.add_reaction(await config.get_raw("emoji"))
                await ctx.send(_('React-message now set to automatically update'))
            except Exception:
                await ctx.send(_('I had some trouble reacting'))
        else:
            await ctx.send(_('This law does not exist'))

    @ _react_settings.command(name="unlink")
    async def unlink_alternate(self, ctx, message_link):
        """Remove a react-message from the list of messages that automatically updates"""

        rules = RuleManager(self.config.guild(ctx.guild))

        msg = await self.helper._get_linked_message(ctx, message_link)
        if msg is None:
            return await ctx.send(_('Ensure the link is used with {list_command}').format(
                list_command=f'`{ctx.prefix}reactset auto_list`'))
        link = await self.helper._format_message_link(msg)

        await self.helper._remove_reactions(ctx, rules, link)
        removed = await rules.remove_link_setting("react_rules", "link", link["link"])
        if removed:
            await ctx.send(_('React-message removed from list'))
        else:
            await ctx.send(_('Message was never set as a react-message'))

    @ commands.Cog.listener()
    async def on_message(self, message):

        if message.author.id == self.bot.user.id:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        content = message.content

        if content == '' or content[0] != "§":  # hardcoded atm
            return

        split = content.split('§')
        num = split[1]

        if num == '':
            return

        # crap way to avoid running when a command runs
        try:
            int(num.split()[0])
        except ValueError:
            return

        rules = RuleManager(self.config.guild(message.guild))

        lov = await rules.get_settings("default_rule")
        rule_text, date = await rules.get_rule_text(lov)

        context = message.channel

        if rule_text is None:
            return await context.send(
                '{_not_default}.\n\n**{_these}**:\n{_formated}'.format(
                    _not_default=_('There needs to be a default law for this guild for this to work'),
                    _these=_('The following laws are in the lawbook'),
                    _formated=await rules.get_rules_formatted()
                )
            )

        if rule_text == "":
            return await context.send(_('This law is completely empty'))

        # Get only specified rules
        partial_rules = ""
        no_dupes = await rules.remove_duplicates(num.split())
        for rule in no_dupes:
            ruleregex = r"(§ *" + re.escape(rule) + r"[a-z]?: [\S ]*)"
            m = re.search(ruleregex, rule_text)
            if m is not None:
                partial_rules += m.groups()[0] + "\n"

        if partial_rules == '':
            return
        await context.send(embed=await self.helper._create_embed(partial_rules, date))

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.react_action(payload)

    @ commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.react_action(payload)

    @ commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        config = self.config.guild(msg.guild)

        rules = RuleManager(config)

        emoji = await config.get_raw("emoji")
        react_messages = await rules.get_settings('react_rules')

        if payload.message_id not in react_messages:
            return
        rules = RuleManager(config)
        await asyncio.sleep(1)
        await msg.add_reaction(emoji)

    async def react_action(self, payload):

        if payload.guild_id is None:
            return

        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        config = self.config.guild(msg.guild)
        rules = RuleManager(config)

        emoji = await config.get_raw("emoji")
        react_messages = await rules.get_settings('react_rules')

        if payload.message_id not in [rmessage['message'] for rmessage in react_messages]:
            return

        if str(payload.emoji) == emoji:
            if payload.event_type == "REACTION_REMOVE" and payload.user_id == self.bot.user.id:
                await msg.add_reaction(emoji)

            if payload.event_type == "REACTION_ADD" and payload.user_id != self.bot.user.id:
                user = self.bot.get_user(payload.user_id)
                try:
                    await msg.remove_reaction(emoji, user)
                except Exception:
                    await channel.send("{} {}".format(_('Tell a mod to fix my perms'), user.mention))
                await self._dm_rules(rules, user, msg)
        else:
            if payload.event_type == "REACTION_ADD" and payload.user_id != self.bot.user.id:
                await msg.clear_reactions()

    async def _dm_rules(self, rules, user, msg):
        react_rules = await rules.get_settings('react_rules')
        rule_name = None
        for rule in react_rules:
            if rule["message"] == msg.id:
                rule_name = rule["name"]

        if rule_name is None:
            return

        rule_text, date = await rules.get_rule_text(rule_name, alternate=True)
        try:
            embed = await self.helper._create_embed(rule_text, date)
            await user.send(embed=embed)
        except discord.Forbidden:
            if msg.author.permissions_in(msg.channel):
                await msg.channel.send("{} {}".format(_("I can't send you messages"), user.mention))
