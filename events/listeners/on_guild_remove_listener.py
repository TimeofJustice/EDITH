import nextcord

import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, guild: nextcord.Guild):
        guild_settings = self.__mysql.select(table="guilds",
                                             colms="settings",
                                             clause=f"WHERE guilds.id={guild.id}")[0]

        guild_settings_id = guild_settings["settings"]

        self.__mysql.delete(table="custom_channels", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="guilds", clause=f"WHERE id={guild.id}")
        self.__mysql.delete(table="instances", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="scm_creators", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="scm_roles", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="scm_rooms", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="scm_room_roles", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="scm_users", clause=f"WHERE guild_id={guild.id}")
        self.__mysql.delete(table="settings", clause=f"WHERE id='{guild_settings_id}'")
