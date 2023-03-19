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

        settings = self.__mysql.select(table="settings", colms="leave_msg, msg_channel",
                                       clause=f"WHERE id='{guild_settings['settings']}'")[0]

        channel_id = settings["msg_channel"]
        channel = member.guild.get_channel(int(channel_id)) if channel_id else None

        if channel and settings["leave_msg"]:
            embed = nextcord.Embed(
                description=settings["leave_msg"]
                .replace("[member]", member.display_name)
                .replace("[guild]", guild.name),
                colour=nextcord.Colour.red()
            )

            await channel.send(embed=embed)
