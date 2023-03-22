import nextcord

import db
from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        guild = self.__interaction.guild

        guild_data = db.Guild.get_or_none(id=guild.id)

        if self.__data["level"] != 0 and guild_data.settings.logging_level == 0:
            category = await guild.create_category(name="E.D.I.T.H Logging")
            messages_channel = await category.create_text_channel(name="messages")

            db.CustomChannel.create(id=category.id, guild=guild.id)
            db.CustomChannel.create(id=messages_channel.id, guild=guild.id)

            await category.set_permissions(guild.default_role, view_channel=False)

            guild_data.settings.log_category = category.id
            guild_data.settings.messages_channel = messages_channel.id
            guild_data.settings.logging_level = self.__data['level']
            guild_data.settings.save()

            embed = nextcord.Embed(
                description="The logging-tool is now enabled!",
                colour=nextcord.Colour.green()
            )
        elif self.__data["level"] != 0 and guild_data.settings.logging_level != 0:
            embed = nextcord.Embed(
                description="The logging-tool was updated to the given level!",
                colour=nextcord.Colour.green()
            )

            guild_data.settings.logging_level = self.__data['level']
            guild_data.settings.save()
        elif self.__data["level"] == 0 and guild_data.settings.logging_level != 0:
            category = guild.get_channel(guild_data.settings.log_category)
            channels = category.channels

            for channel in channels:
                await channel.delete()

            await category.delete()

            guild_data.settings.log_category = None
            guild_data.settings.messages_channel = None
            guild_data.settings.logging_level = 0
            guild_data.settings.save()

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
