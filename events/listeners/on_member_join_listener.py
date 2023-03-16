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
        if role_id is not None:
            role = guild.get_role(int(role_id))
        else:
            role = None

        channel_id = settings["msg_channel"]
        if channel_id is not None:
            channel = guild.get_channel(int(channel_id))
        else:
            channel = None

        if role is not None:
            await member.add_roles(role)

        if channel is not None and settings["welcome_msg"] is not None:
            embed = nextcord.Embed(
                description=settings["welcome_msg"]
                .replace("[member]", member.display_name)
                .replace("[guild]", guild.name),
                colour=nextcord.Colour.green()
            )

            await channel.send(embed=embed)
