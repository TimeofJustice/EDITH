import json

import nextcord

from events import command
from mysql_bridge import Mysql


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["command"] == "default":
            guild_settings = self.__mysql.select(table="guilds",
                                                 colms="settings",
                                                 clause=f"WHERE guilds.id={self.__guild.id}")[0]

            self.__mysql.update(table="settings", value=f"default_role='{self.__data['role'].id}'",
                                clause=f"WHERE id='{guild_settings['settings']}'")

            embed = nextcord.Embed(
                description=f"Default role is now active!",
                colour=nextcord.Colour.green()
            )

            embed.add_field(
                name="Role",
                value=f"**@{self.__data['role'].name}** ({self.__data['role'].id})",
                inline=True
            )

            embed.set_author(
                name="Settings",
                icon_url="https://cdn-icons-png.flaticon.com/512/81/81020.png"
            )

            await self.__interaction.send(embed=embed, ephemeral=True)

            print(self.__data["role"])
        elif self.__data["command"] == "notifications":
            await self.__interaction.response.send_modal(
                NotificationsModal(self.__guild, self.__data, self.__bot_instance)
            )
        elif self.__data["command"] == "disable":
            pass


class NotificationsModal(nextcord.ui.Modal):
    def __init__(self, guild, data, bot_instance):
        self.__mysql = Mysql()
        self.__guild = guild
        self.__data = data
        self.__bot_instance = bot_instance
        super().__init__("Settings (Notifications)")

        self.__join = nextcord.ui.TextInput(label=f"What should be the join message?",
                                            style=nextcord.TextInputStyle.paragraph,
                                            placeholder=f"Member-Name: [member]\n"
                                                        f"Guild-Name: [guild]",
                                            max_length=120, required=True)
        self.add_item(self.__join)

        self.__leave = nextcord.ui.TextInput(label=f"What should be the leave message?",
                                             style=nextcord.TextInputStyle.paragraph,
                                             placeholder=f"Member-Name: [member]\n"
                                                         f"Guild-Name: [guild]",
                                             max_length=120, required=True)
        self.add_item(self.__leave)

    async def callback(self, interaction: nextcord.Interaction):
        guild_settings = self.__mysql.select(table="guilds",
                                             colms="settings",
                                             clause=f"WHERE guilds.id={self.__guild.id}")[0]

        self.__mysql.update(table="settings", value=f"welcome_msg='{self.__join.value}'",
                            clause=f"WHERE id='{guild_settings['settings']}'")
        self.__mysql.update(table="settings", value=f"leave_msg='{self.__leave.value}'",
                            clause=f"WHERE id='{guild_settings['settings']}'")
        self.__mysql.update(table="settings", value=f"msg_channel='{self.__data['channel'].id}'",
                            clause=f"WHERE id='{guild_settings['settings']}'")

        embed = nextcord.Embed(
            description=f"Notifications are now active!",
            colour=nextcord.Colour.green()
        )

        embed.add_field(
            name="Join",
            value=f"`{self.__join.value}`",
            inline=True
        )

        embed.add_field(
            name="Leave",
            value=f"`{self.__leave.value}`",
            inline=True
        )

        embed.add_field(
            name="Channel",
            value=f"**#{self.__data['channel'].name}** ({self.__data['channel'].id})",
            inline=True
        )

        embed.set_author(
            name="Settings",
            icon_url="https://cdn-icons-png.flaticon.com/512/81/81020.png"
        )

        await interaction.send(embed=embed, ephemeral=True)
