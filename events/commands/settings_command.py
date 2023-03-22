import nextcord

import db
from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["command"] == "default":
            guild = db.Guild.get_or_none(id=self.__guild.id)

            guild.settings.default_role = self.__data['role'].id
            guild.settings.save()

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
        elif self.__data["command"] == "notifications":
            await self.__interaction.response.send_modal(
                NotificationsModal(self.__guild, self.__data, self.__bot_instance)
            )
        elif self.__data["command"] == "disable":
            guild = db.Guild.get_or_none(id=self.__guild.id)

            if self.__data["method"] == "notifications":
                guild.settings.msg_channel = None
                guild.settings.save()

                embed = nextcord.Embed(
                    description=f"Notifications are now disabled!",
                    colour=nextcord.Colour.red()
                )
            else:
                guild.settings.default_role = None
                guild.settings.save()

                embed = nextcord.Embed(
                    description=f"Default role is now disabled!",
                    colour=nextcord.Colour.red()
                )

            embed.set_author(
                name="Settings",
                icon_url="https://cdn-icons-png.flaticon.com/512/81/81020.png"
            )

            await self.__interaction.send(embed=embed, ephemeral=True)
        elif self.__data["command"] == "show":
            guild = db.Guild.get_or_none(id=self.__guild.id)

            role_id = guild.settings.default_role
            if role_id is not None:
                role = self.__guild.get_role(int(role_id))
            else:
                role = None

            channel_id = guild.settings.msg_channel
            if channel_id is not None:
                channel = self.__guild.get_channel(int(channel_id))
            else:
                channel = None

            embed = nextcord.Embed(
                description=f"The current settings are:",
                colour=nextcord.Colour.blue()
            )

            if role is not None:
                embed.add_field(
                    name="Default role",
                    value=f"**@{role.name}** ({role.id})",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Default role",
                    value=f"**Not active**",
                    inline=False
                )

            if (guild.settings.welcome_msg is not None or guild.settings.leave_msg is not None) and channel is not None:
                embed.add_field(
                    name="Notifications",
                    value=f"Join-Message: `{guild.settings.welcome_msg}`\n"
                          f"Leave-Message: `{guild.settings.leave_msg}`\n"
                          f"Message-Channel: **#{channel.name}** ({channel.id})",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Notifications",
                    value="**Not active**",
                    inline=False
                )

            embed.set_author(
                name="Settings",
                icon_url="https://cdn-icons-png.flaticon.com/512/81/81020.png"
            )

            await self.__interaction.send(embed=embed, ephemeral=True)


class NotificationsModal(nextcord.ui.Modal):
    def __init__(self, guild, data, bot_instance):
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
        guild = db.Guild.get_or_none(id=self.__guild.id)

        guild.settings.welcome_msg = self.__join.value
        guild.settings.leave_msg = self.__leave.value
        guild.settings.msg_channel = self.__data['channel'].id
        guild.settings.save()

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
