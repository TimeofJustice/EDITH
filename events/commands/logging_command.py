import nextcord

from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(interaction, bot_instance, data)

    async def run(self):
        guild = self.__interaction.guild

        guild_settings = self.__mysql.select(table="guilds",
                                             colms="guilds.id, settings.log_category, settings.id AS settings_id, "
                                                   "settings.logging_level",
                                             clause=f"INNER JOIN settings ON guilds.settings=settings.id "
                                                    f"WHERE guilds.id={guild.id}")[0]

        if self.__data["level"] != 0 and guild_settings["logging_level"] == 0:
            category = await guild.create_category(name="E.D.I.T.H Logging")
            messages_channel = await category.create_text_channel(name="messages")

            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)", values=(category.id, guild.id))
            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)", values=(messages_channel.id, guild.id))

            await category.set_permissions(guild.default_role, view_channel=False)

            self.__mysql.update(table="settings", value=f"log_category={category.id}",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")
            self.__mysql.update(table="settings", value=f"messages_channel={messages_channel.id}",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")
            self.__mysql.update(table="settings", value=f"logging_level={self.__data['level']}",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")

            embed = nextcord.Embed(
                description="The logging-tool is now enabled!",
                colour=nextcord.Colour.green()
            )
        elif self.__data["level"] != 0 and guild_settings["logging_level"] != 0:
            embed = nextcord.Embed(
                description="The logging-tool was updated to the given level!",
                colour=nextcord.Colour.green()
            )

            self.__mysql.update(table="settings", value=f"logging_level={self.__data['level']}",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")
        elif self.__data["level"] == 0 and guild_settings["logging_level"] != 0:
            category = guild.get_channel(guild_settings["log_category"])
            channels = category.channels

            for channel in channels:
                await channel.delete()

            await category.delete()

            self.__mysql.update(table="settings", value=f"log_category=Null",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")
            self.__mysql.update(table="settings", value=f"messages_channel=Null",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")
            self.__mysql.update(table="settings", value=f"logging_level=0",
                                clause=f"WHERE id='{guild_settings['settings_id']}'")

            embed = nextcord.Embed(
                description="The logging-tool is now disabled!",
                colour=nextcord.Colour.orange()
            )
        else:
            embed = nextcord.Embed(
                description="The logging-tool is already off!",
                colour=nextcord.Colour.red()
            )

        await self.__interaction.send(embed=embed, ephemeral=True)
