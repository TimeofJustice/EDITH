import nextcord

import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, member: nextcord.Member):
        guild = member.guild

        guild_settings = self.__mysql.select(table="guilds",
                                             colms="settings",
                                             clause=f"WHERE guilds.id={guild.id}")[0]

        settings = self.__mysql.select(table="settings", colms="default_role, welcome_msg, msg_channel",
                                       clause=f"WHERE id='{guild_settings['settings']}'")[0]

        role_id = settings["default_role"]
        role = member.guild.get_role(int(role_id)) if role_id else None

        channel_id = settings["msg_channel"]
        channel = member.guild.get_channel(int(channel_id)) if channel_id else None

        if role:
            await member.add_roles(role)

        if channel and settings["welcome_msg"]:
            embed = nextcord.Embed(
                description=settings["welcome_msg"]
                .replace("[member]", member.display_name)
                .replace("[guild]", guild.name),
                colour=nextcord.Colour.green()
            )

            await channel.send(embed=embed)
