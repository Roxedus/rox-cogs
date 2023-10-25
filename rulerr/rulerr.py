# Bot Packages
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

import asyncio
import logging
import re
from typing import Optional, Union

from .helpers import RuleHelper
from .manager import RuleManager

_ = Translator('Rulerr', __file__)


@cog_i18n(_)
class Rulerr(commands.Cog):
    """Cog to manage ruleset with rules"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=9783465975, force_registration=True)
        default_settings = {
            "agreement_msg": {},
            "agreement_role": "",
            "alt_emoji": "\N{INCOMING ENVELOPE}",
            "auto_update": [],
            "channel": {},
            "default_rule": None,
            "emoji": "\N{THUMBS UP SIGN}",
            "interface_lang": "en_en",
            "react_rules": [],
            "rule_prefix": "§",
            "rules": {},
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
    async def rules(self, ctx, user: Optional[discord.Member] = None, ruleset: Union[int, str] = None, *, num: str = None):
        """Command to explicit get the rules in a ruleset"""

        law = ruleset

        if isinstance(law, str):
            law = law.lower()

        content = "{}! {}".format(user.mention, _(
            'Hey please read the rules')) if user else None
        embed = None

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)

        if isinstance(law, int):
            if num is None:
                num = str(law)
            else:
                num = str(law) + " " + num
            law = await rules.get_settings("default_rule")

        rule_text, date = await rules.get_rule_text(law)

        formatted = await rules.get_rules_formatted()

        if not formatted:
            return await ctx.send(_('There is currently no rulesets set up'))

        if rule_text is None:
            return await ctx.send("**{_txt}:**\n{_list}".format(_txt=_('Lists all rulesets for this guild'),
                                                                _list=formatted))

        if rule_text == "":
            return await ctx.send(_('This ruleset is completely empty'))

        # Get only specified rules
        if num is not None:
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
                embed = await self.helper._create_embed(
                    "**{_txt} {law}**\n".format(
                        _txt=_('The rules for the ruleset'), law=law) + partial_rules
                )
            else:
                embed = await self.helper._create_embed(partial_rules, date)
        else:
            embed = await self.helper._create_embed(rule_text, date)
        if embed:
            embed.title = "Someone wants to remind you about the rules:"
            await ctx.send(content=content, embed=embed)
        else:
            await ctx.send("Could not build rule embed")

    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="rset")
    async def _rule_set(self, ctx):
        """Group for managing rulesets and rules"""

    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    @_rule_set.group(name="rulesets")
    async def _rule_settings(self, ctx):
        """Commands for managing rulesets and rules"""

    @_rule_settings.command(name="list")
    async def listrules(self, ctx):
        """Lists the current rulesets"""
        rules = RuleManager(self.config.guild(ctx.guild))
        await ctx.send("**{}**:\n{}".format(
            _('The following rulesets are configured'), await rules.get_rules_formatted()))

    @_rule_settings.command(name="new")
    async def newrules(self, ctx, ruleset, *, newrule: str = None):
        """Create a new ruleset, with rules"""

        law = ruleset

        if law is not None:
            law = law.lower()

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        added = await rules.add_rule(law, newrule)
        new_rule = await config.rules.get_raw(law)

        title = (_('The ruleset {ruleset} already exists') if not added else _(
            'Ruleset {ruleset} added')).format(ruleset=law)

        description = _('RuleText') + \
            f':\n```diff\n{new_rule["rule_text"][:980]}\n```'
        if new_rule.get('alternate'):
            description += "\n" + \
                _('AltText') + \
                f':\n```diff\n{new_rule["alternate"][:980]}\n```'

        embed = discord.Embed(title=title, colour=ctx.me.colour)
        embed.description = description
        embed.add_field(name=_('Edited at'),
                        value=new_rule['edited'].split(".")[0])
        await ctx.send(embed=embed)

    @ _rule_settings.command(name="plaintext")
    async def plaintext(self, ctx, ruleset):
        """Sends the ruleset in plaintext"""

        law = ruleset

        if law is not None:
            law = law.lower()

        try:
            rule_text = await self.config.guild(ctx.guild).rules.get_raw(law)
            await ctx.send("```\n" + rule_text["rule_text"] + "\n```")
        except KeyError:
            await ctx.send(_('Please ensure {ruleset} is a valid ruleset').format(ruleset=law))

    @ _rule_settings.command(name="remove")
    async def removerules(self, ctx, ruleset):
        """Removes the plaintext"""

        law = ruleset

        if law is not None:
            law = law.lower()

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        await self.helper._remove_reactions(ctx, rules, law)
        try:
            await rules.remove_rule(law)
            await ctx.send(_('Ruleset removed'))
        except KeyError:
            await ctx.send(_('This ruleset does not exist'))

    @ _rule_settings.command(name="update")
    async def updaterules(self, ctx, ruleset, *, newrule):
        """Updates the ruleset"""

        law = ruleset

        if law is not None:
            law = law.lower()

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        try:
            await rules.edit_rule(law, newrule)
            await self.helper._update_messages(ctx, rules)
        except KeyError:
            await ctx.send(_('Could not find this ruleset'))

    @ _rule_settings.command(name="default")
    async def set_default_rule(self, ctx, ruleset):
        """Set the default ruleset for this guild"""

        law = ruleset

        if law is not None:
            law = law.lower()

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        # pylint: disable=unused-variable
        rule_text, date = await rules.get_rule_text(law)

        if rule_text is None:
            return await ctx.send(
                "{_not}.\n\n**{_these}**:\n{_formatted}".format(
                    _not=_('This ruleset is not configured'),
                    _these=_('The following rulesets are configured'),
                    _formatted=await rules.get_rules_formatted()
                )
            )
        await rules.change_setting("default_rule", law)
        await ctx.send(_('{ruleset} is now the default ruleset').format(ruleset=law))

    @ _rule_settings.command(name="prefix")
    async def set_prefix(self, ctx, prefix):
        """Set the default on_message prefix for this guild"""

        if prefix is not None:
            prefix = prefix.lower()

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)

        await rules.change_setting("rule_prefix", prefix)
        await ctx.send(_('{prefix} is now the default prefix').format(prefix=prefix))

    @ commands.guild_only()
    @ commands.has_permissions(manage_messages=True)
    @ _rule_set.group(name="auto")
    async def _auto_settings(self, ctx):
        """Commands for setting up automatically message updating"""

    @ _auto_settings.command(name="post")
    async def postauto(self, ctx, ruleset):
        """Sends a message that automatically updates when the ruleset updates"""

        law = ruleset

        if law is not None:
            law = law.lower()

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        rule_text, date = await rules.get_rule_text(law)

        if rule_text is None:
            return await ctx.send(
                "{_not}.\n\n**{_these}**:\n{_formatted}".format(
                    _not=_('This ruleset is not configured'),
                    _these=_('The following rulesets are configured'),
                    _formatted=await rules.get_rules_formatted()
                )
            )

        if rule_text == "":
            return await ctx.send(_('This ruleset is completely empty'))

        embed = await self.helper._create_embed(rule_text, date)
        msg = await ctx.send(embed=embed)
        await rules.add_link_setting("auto_update", law, await self.helper._format_message_link(msg))

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
    async def autorules(self, ctx, ruleset, link):
        """Adds a old message from the bot to the list of automatically updated messages"""

        law = ruleset

        if law is not None:
            law = law.lower()

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
            await ctx.send(_('This ruleset does not exist'))

        await self.helper._update_messages(ctx, rules, name=law)

    @ _auto_settings.command(name="list")
    async def _auto_list(self, ctx):
        """Sends a list of the messages set up to automatically update"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        auto_update_messages = await rules.get_settings("auto_update")

        if len(auto_update_messages) == 0:
            return await ctx.send(_('No message is currently set up for automatic updates'))

        embed = await self.helper._create_embed()
        embed.title = "**{}:**".format(
            _('Messages set to automatically update'))

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
    @ _rule_set.group(name="alternate", aliases=["alt"])
    async def _alt_settings(self, ctx):
        """Commands for setting up alternate rules to DMs triggered by reactions"""

    @ _alt_settings.command(name="update")
    async def edit_alternate(self, ctx, ruleset, *, newrule):
        """Update the ruleset with a alternate version"""

        law = ruleset

        if law is not None:
            law = law.lower()

        rules = RuleManager(self.config.guild(ctx.guild))
        try:
            await rules.edit_rule(law, newrule, alternate=True)
            await ctx.send(_('Alternate ruleset updated'))
        except KeyError:
            await ctx.send(_('Could not find this ruleset'))

    @ _alt_settings.command(name="remove")
    async def remove_alternate(self, ctx, ruleset):
        """Removes the alternate ruleset attached to the main ruleset"""

        law = ruleset

        if law is not None:
            law = law.lower()

        rules = RuleManager(self.config.guild(ctx.guild))
        try:
            await rules.remove_rule(law, alternate=True)
            await ctx.send(_('Alternate ruleset removed'))
        except KeyError:
            await ctx.send(_('Could not find this ruleset'))

    @ _alt_settings.command(name="list")
    async def show_alternate(self, ctx, ruleset: str = None):
        """Lists the alternate rulesets attached to the ruleset"""

        law = ruleset

        if law is not None:
            law = law.lower()

        rules = RuleManager(self.config.guild(ctx.guild))
        # pylint: disable=unused-variable
        rule_text, date = await rules.get_rule_text(law, alternate=True)
        if rule_text is not None:
            await ctx.send("```\n" + rule_text + "\n```")
        else:
            return await ctx.send("**{_txt}:**\n{_list}".format(_txt=_('Lists all alternate ruleset for this guild'),
                                                                _list=await rules.get_rules_formatted(alternate=True)))

    @ _alt_settings.command(name="auto_list")
    async def _react_list(self, ctx):
        """Lists the alternate rulesets set up with reactions"""

        rules = RuleManager(self.config.guild(ctx.guild))
        react_messages = await rules.get_settings("react_rules")

        list_message = "**{}:**\n".format(
            _('Reaction-messages set to automatically update'))

        if len(react_messages) == 0:
            return await ctx.send(_('No reaction-message is currently set up for automatic updates'))

        for message in react_messages:
            list_message += f'{message["name"]}: {message["link"]}\n'

        await ctx.send(list_message)

    @ _alt_settings.command(name="link")
    async def link_alternate(self, ctx, ruleset, link):
        """Adds a old message from the bot to the list of automatically updated react-messages"""

        law = ruleset

        if law is not None:
            law = law.lower()

        msg = await self.helper._get_linked_message(ctx, link)
        if msg is None:
            return await ctx.send(_('Could not find the message'))
        if msg.author != self.bot.user:
            return await ctx.send(_('This only works on messages owned by the bot'))

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)
        added = await rules.add_link_setting("react_rules", law, await self.helper._format_message_link(msg))

        if added == -1:
            await ctx.send(_('Message already set to automatically update'))
        elif added:
            try:
                await msg.clear_reactions()
                await asyncio.sleep(1)
                await msg.add_reaction(await config.get_raw("alt_emoji"))
                await ctx.send(_('React-message now set to automatically update'))
            except Exception:
                await ctx.send(_('I had some trouble reacting'))
        else:
            await ctx.send(_('This ruleset does not exist'))

    @ _alt_settings.command(name="unlink")
    async def unlink_alternate(self, ctx, message_link):
        """Remove a react-message from the list of messages that automatically updates"""

        rules = RuleManager(self.config.guild(ctx.guild))

        msg = await self.helper._get_linked_message(ctx, message_link)
        if msg is None:
            return await ctx.send(_('Ensure the link is used with {list_command}').format(
                list_command=f"`{ctx.prefix}reactset auto_list`"))
        link = await self.helper._format_message_link(msg)

        await self.helper._remove_reactions(ctx, rules, link)
        removed = await rules.remove_link_setting("react_rules", "link", link["link"])
        if removed:
            await ctx.send(_('React-message removed from list'))
        else:
            await ctx.send(_('Message was never set as a react-message'))

    @ commands.guild_only()
    @ commands.has_permissions(manage_messages=True)
    @ _rule_set.group(name="react")
    async def _react_settings(self, ctx):
        """Commands for setting reaction based rule-agreement"""

    @ _react_settings.command(name="set")
    async def set_react(self, ctx, message_link):
        """Sets the reaction based rule-agreement"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)

        msg = await self.helper._get_linked_message(ctx, message_link)

        if await config.get_raw("agreement_role") == "":
            return await ctx.send(_('There is no agreement role set'))
        elif msg is None:
            return await ctx.send(_('Could not find the message'))
        elif msg.author != self.bot.user:
            return await ctx.send(_('This only works on messages owned by the bot'))

        if not [rule for rule in await rules.get_settings("auto_update") if rule["message"] == int(msg.id)]:
            _yes = await ctx.send(_('This is not a auto updating message, '
                                    'would you like to make it one based on the default rule?'))
            start_adding_reactions(_yes, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(_yes, ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30.0)
                if pred.result:
                    await _yes.delete()
                    law = await rules.get_settings("default_rule")
                    await rules.add_link_setting("auto_update", law, await self.helper._format_message_link(msg))
                    await self.helper._update_messages(ctx, rules, name=law, nomsg=True)
                else:
                    await _yes.delete()
                    await ctx.react_quietly("❎")
            except asyncio.exceptions.TimeoutError:
                await _yes.delete()
                await ctx.react_quietly("❎")

        if await rules.get_settings("agreement_msg"):
            _yes = await ctx.send(_('There is already a agreement message set up for this guild, overwrite?'))
            start_adding_reactions(_yes, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(_yes, ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30.0)
                if pred.result:
                    await _yes.delete()
                else:
                    await _yes.delete()
                    return await ctx.react_quietly("❎")
            except asyncio.exceptions.TimeoutError:
                await _yes.delete()
                return await ctx.react_quietly("❎")

        await rules.change_setting("agreement_msg", await self.helper._format_message_link(msg))
        await ctx.tick()
        await msg.add_reaction(await config.get_raw("emoji"))
        txt = f"[{_('This is now the agreement message')}]({msg.jump_url})"
        embed = await self.helper._create_embed(txt)
        embed.set_footer(text=_('Edited at'))
        embed.timestamp = msg.created_at
        await ctx.send(embed=embed)

    @ _react_settings.command(name="get")
    async def get_react(self, ctx):
        """Gets the message for the reaction based rule-agreement"""

        config = self.config.guild(ctx.guild)
        rules = RuleManager(config)

        try:
            link = await rules.get_settings("agreement_msg", "link")
        except KeyError:
            return await ctx.send(_('No react message is set'))
        msg = await self.helper._get_linked_message(ctx, link)

        if not msg:
            return await ctx.send(_('No react message is set'))

        txt = f"[{_('This is agreement message')}]({msg.jump_url})"
        embed = await self.helper._create_embed(txt)
        embed.set_footer(text=_('Edited at'))
        embed.timestamp = msg.created_at
        await ctx.send(embed=embed)

    @ _react_settings.command(name="role")
    async def set_react_role(self, ctx, role: discord.Role):
        """Sets the role for the reaction based rule-agreement"""

        config = self.config.guild(ctx.guild)
        await config.agreement_role.set(role.id)
        msg_txt = role.mention + " " + \
            _('is now the role assigned on agreement')
        embed = await self.helper._create_embed(text=msg_txt)
        await ctx.send(embed=embed)

    @ _react_settings.command(name="remove")
    async def remove_react(self, ctx):
        """Removes the message for the reaction based rule-agreement from the list"""

        config = self.config.guild(ctx.guild)

        try:
            msg = await ctx.channel.fetch_message(await config.get_raw("agreement_msg", "message"))
            await msg.remove_reaction(await config.get_raw("emoji"), self.bot.user)
        except KeyError:
            pass

        await config.agreement_msg.clear()

        embed = await self.helper._create_embed(_('Cleared the agreement message'))
        await ctx.send(embed=embed)

    @ commands.Cog.listener()
    async def on_message(self, message):

        if message.author.id == self.bot.user.id:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        content = message.content

        config = self.config.guild(message.guild)
        prefix = await config.get_raw("rule_prefix")

        if content == "" or content[0] != prefix:
            return

        split = content.split(prefix)
        num = split[1]

        if num == "":
            return

        # crap way to avoid running when a command runs
        try:
            int(num.split()[0])
        except ValueError:
            return

        rules = RuleManager(config)

        lov = await rules.get_settings("default_rule")
        rule_text, date = await rules.get_rule_text(lov)

        context = message.channel

        if rule_text is None:
            return await context.send(
                "{_not_default}.\n\n**{_these}**:\n{_formatted}".format(
                    _not_default=_(
                        'There needs to be a default ruleset for this guild for this to work'),
                    _these=_('The following rulesets are configured'),
                    _formatted=await rules.get_rules_formatted()
                )
            )

        if rule_text == "":
            return await context.send(_('This ruleset is completely empty'))

        # Get only specified rules
        partial_rules = ""
        no_dupes = await rules.remove_duplicates(num.split())
        for rule in no_dupes:
            ruleregex = r"(§ *" + re.escape(rule) + r"[a-z]?: [\S ]*)"
            m = re.search(ruleregex, rule_text)
            if m is not None:
                partial_rules += m.groups()[0] + "\n"

        if partial_rules == "":
            return

        usrs = [user.mention for user in message.mentions if not user.bot and (
            user.id != message.author.id)] if message.mentions else None
        text = "{}! {}".format(', '.join(usrs), _(
            'Hey please read the rules')) if usrs else None

        embed = await self.helper._create_embed(partial_rules, date)
        embed.title = "Someone wants to remind you about the rules:"
        await context.send(content=text, embed=embed)

    @ commands.Cog.listener(name="on_raw_reaction_add")
    async def on_agreement_reaction(self, payload):
        if payload.guild_id is None:
            return

        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        config = self.config.guild(msg.guild)
        emoji = await config.get_raw("emoji")
        role = await config.get_raw("agreement_role")

        if not role:
            return

        role = msg.guild.get_role(role)

        if payload.message_id != await config.get_raw("agreement_msg", "message"):
            return

        if str(payload.emoji) == emoji:
            if payload.event_type == "REACTION_ADD" and payload.user_id != self.bot.user.id:
                user = payload.member
                try:
                    await user.add_roles(role, reason=_('Agreed to the rules'))
                    await msg.remove_reaction(emoji, user)
                except Exception:
                    if msg.channel.permissions_for(user).send_messages:
                        await channel.send("{} {}".format(_('Tell a mod to fix my perms'), user.mention))
                    else:
                        self.log.info(
                            "The bot is missing perms in %s to agree" % (msg.guild.name))
        else:
            if payload.event_type == "REACTION_ADD" and payload.user_id != self.bot.user.id:
                await msg.remove_reaction(payload.emoji, payload.member)

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.alt_action(payload)

    @ commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.alt_action(payload)

    @ commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        config = self.config.guild(msg.guild)

        rules = RuleManager(config)

        emoji = await config.get_raw("alt_emoji")
        react_messages = await rules.get_settings("react_rules")

        if payload.message_id not in react_messages:
            return
        rules = RuleManager(config)
        await asyncio.sleep(1)
        await msg.add_reaction(emoji)

    async def alt_action(self, payload):
        if payload.guild_id is None:
            return

        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        config = self.config.guild(msg.guild)
        rules = RuleManager(config)

        emoji = await config.get_raw("alt_emoji")
        react_messages = await rules.get_settings("react_rules")

        if payload.message_id not in [rmessage["message"] for rmessage in react_messages]:
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
        react_rules = await rules.get_settings("react_rules")
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
