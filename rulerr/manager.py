from datetime import datetime


class RuleManager:
    def __init__(self, config):
        self.config = config

    async def add_rule(self, name, rule_text, alternaterule: str = None):
        if name is not None:
            name = name.lower()

        if any(rule for rule in await self.config.rules() if rule == name):
            return False

        rule_text = rule_text if rule_text else ""

        async with self.config.rules() as rules:
            rules[name] = {
                "rule_text": rule_text,
                "alternate": alternaterule,
                "edited": str(datetime.utcnow())
            }
        return True

    async def remove_rule(self, name, alternate: bool = False):
        if name is not None:
            name = name.lower()
        _rule = await self.config.rules.get_raw(name)
        if _rule is not None:
            if alternate:
                await self.config.rules.set_raw(name, "alternate", value=None)
                await self.remove_link_setting("react_rules", "name", name)
            else:
                await self.config.rules.clear_raw(name)
                await self.remove_link_setting("auto_update", "name", name)
                await self.remove_link_setting("react_rules", "name", name)
                if name == await self.config.default_rule():
                    await self.config.default_rule.set(None)
            return True
        return False

    async def edit_rule(self, name, new_rule_text, alternate: bool = False):
        if name is not None:
            name = name.lower()
        try:
            async with self.config.rules() as _rule:
                if alternate:
                    _rule[name]["alternate"] = new_rule_text
                else:
                    _rule[name]["rule_text"] = new_rule_text
                _rule[name]["edited"] = str(datetime.utcnow())
            return True
        except KeyError:
            return False

    async def get_rule_text(self, name, alternate: bool = False):
        if name is not None:
            name = name.lower()
        _rule = self.config.rules
        try:
            if alternate:
                return await _rule.get_raw(name, "alternate"), await _rule.get_raw(name, "edited")
            else:
                return await _rule.get_raw(name, "rule_text"), await _rule.get_raw(name, "edited")
        except KeyError:
            return None, None

    async def get_rules_formatted(self, alternate: bool = False):
        rules = await self._get_rule_names(alternate)
        formatted_rules = ""
        for rule in rules:
            if rule == await self.config.default_rule():
                formatted_rules = "•" + rule.capitalize() + "\n" + formatted_rules
            else:
                formatted_rules += "•" + rule.capitalize() + "\n"
        return formatted_rules

    async def _get_rule(self, name=None):
        return await self.config.rules.get_raw(name)

    async def add_link_setting(self, setting, name, link):
        if name is not None:
            name = name.lower()
        # pylint: disable=unused-variable
        rule, date = await self.get_rule_text(name)
        if rule is not None:
            if any(msg for msg in await self.config.get_raw(setting) if msg["link"] == link.get("link")):
                return -1
            _update = await self.config.get_raw(setting)
            _update.append({"name": name, "channel": link.get("channel"),
                            "message": link.get("message"), "link": link.get("link")})
            await self.config.set_raw(setting, value=_update)
            return True
        return False

    async def remove_link_setting(self, setting, match_type, to_match):
        if to_match is not None:
            to_match = to_match.lower()

        removed = False
        for message in reversed(await self.config.get_raw(setting)):
            if message[match_type] == to_match:
                _update = await self.config.get_raw(setting)
                _update.remove(message)
                await self.config.set_raw(setting, value=_update)
                removed = True
        return removed

    async def get_settings(self, *setting):
        return await self.config.get_raw(*setting)

    async def change_setting(self, setting, value):
        await self.config.set_raw(setting, value=value)

    async def _get_rule_names(self, alternate):
        if alternate:
            return [rule for rule in await self.config.rules()
                    if await self.config.get_raw("rules", rule, "alternate") is not None]
        else:
            return [rule for rule in await self.config.rules()]

    async def remove_duplicates(self, dupe_list):
        seen = {}
        result = []
        for item in dupe_list:
            if item in seen:
                continue
            seen[item] = 1
            result.append(item)
        return result
