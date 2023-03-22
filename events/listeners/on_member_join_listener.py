import nextcord

import db
import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, member: nextcord.Member):
        guild = member.guild
        guild_data = db.Guild.get_or_none(db.Guild.id == guild.id)

        role_id = guild_data.settings.default_role
        role = member.guild.get_role(int(role_id)) if role_id else None

        channel_id = guild_data.settings.msg_channel
        channel = member.guild.get_channel(int(channel_id)) if channel_id else None

        if role:
            await member.add_roles(role)

        if channel and guild_data.settings.welcome_msg:
            embed = nextcord.Embed(
                description=guild_data.settings.welcome_msg
                .replace("[member]", member.display_name)
                .replace("[guild]", guild.name),
                colour=nextcord.Colour.green()
            )

            await channel.send(embed=embed)
