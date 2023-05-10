# Bot Packages
import discord
from redbot.core.i18n import Translator

import asyncio
from datetime import datetime

_ = Translator('Rulerr', __file__)


class RuleHelper:
    def __init__(self, bot):
        self.bot = bot

    async def _update_messages(self, ctx, rules, name=None, nomsg=False):
        auto_update_messages = await rules.get_settings("auto_update")
        agreement_msg = await rules.get_settings("agreement_msg")

        if not nomsg:
            await ctx.send(_('Updating messages'))

        async with ctx.channel.typing():
            s_embed = await self._create_embed(text=_('Messages updated'))
            for message in auto_update_messages:
                if message["name"] == name or name is None:
                    msg = await self._get_linked_message(ctx, message["link"])
                    if msg is None:
                        s_embed.add_field(name=_('Could not find this message'), value=f'[link]({message["link"]})')
                        continue

                    updated_text, date = await rules.get_rule_text(message["name"])
                    if updated_text is None:
                        s_embed.add_field(name=_('Could not find the following ruleset'), value=message["name"])
                        continue

                    await asyncio.sleep(2)
                    embed = await self._create_embed(updated_text, date)
                    content = None

                    if len(msg.embeds) == 1:
                        embed.colour = msg.embeds[0].colour
                    if message.get("message") == agreement_msg.get("message"):
                        content = _('Please react with {emoji} to agree to the rules').format(
                            emoji=await rules.get_settings("emoji"))
                    await msg.edit(content=content, embed=embed)
            if len(s_embed.fields) == 0:
                s_embed.description = _('Updated messages')
            else:
                s_embed.description = _('Some messages could not be found, please remove them manually')

            if not nomsg:
                await ctx.send(embed=s_embed)
            return

    async def _get_linked_message(self, ctx, message_link):
        try:
            message_split = message_link.split("/")
            message_id = int(message_split[-1])
            channel_id = int(message_split[-2])
            guild_id = int(message_split[-3])
        except Exception:
            return None

        if ctx.guild.id != int(guild_id):
            return None

        channel = ctx.guild.get_channel(channel_id)
        if channel is None:
            return None

        try:
            msg = await channel.fetch_message(message_id)
            return msg
        except Exception:
            return None

    async def _create_embed(self, text: str = None, date: str = None):
        avatar = self.bot.user.display_avatar.replace(static_format="png", size=1024).url
        embed = discord.Embed(color=0xD9C04D)
        embed.set_author(name=self.bot.user.name, icon_url=avatar)
        if text:
            embed.description = text
        if date:
            embed.set_footer(text=_('Edited at'))
            embed.timestamp = discord.utils.format_dt(datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f'))
        return embed

    async def _remove_reactions(self, ctx, rules, to_match):
        react_rules = await rules.get_settings("react_rules")
        for rule in react_rules:
            if rule["name"] == to_match or rule["link"] == to_match:
                msg = await self._get_linked_message(ctx, rule["link"])
                if msg is None:
                    await ctx.send("{}:\n<{}>\n{}".format(
                        _('Could not remove the reactions from the following message'),
                        to_match["link"],
                        _('Ensure the bot has access, or delete the reaction manually')
                    )
                    )
                    continue

                await msg.remove_reaction(await ctx.bot.config.guild(ctx.guild).get_raw("alt_emoji"), self.bot.user)

                await asyncio.sleep(2)

    async def _format_message_link(self, msg):
        return {"channel": msg.channel.id, "message": msg.id,
                "link": f"https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"}
