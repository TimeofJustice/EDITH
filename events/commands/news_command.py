import nextcord
import requests

import db
from events import command, instance
from events.commands import news_view


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        guild_entry = db.Guild.get_or_none(db.Guild.id == self.__guild.id)

        if guild_entry is None:
            return

        guild_settings = db.Guild.Setting.get_or_none(db.Guild.Setting.id == guild_entry.settings.id)

        if guild_settings is None:
            return

        if self.__data['subcommand'] == "add":
            if guild_settings.news_category is None:
                category = await self.__guild.create_category("News")

                guild_settings.news_category = category.id
                guild_settings.save()

                channel = await category.create_text_channel("select-roles")
                guild_settings.news_channel = channel.id
                guild_settings.save()
            else:
                category = self.__guild.get_channel(guild_settings.news_category)
                channel = self.__guild.get_channel(guild_settings.news_channel)

            news_channel = await self.__guild.create_text_channel(self.__data["name"], category=category)
            news_role = await self.__guild.create_role(name=self.__data["name"])

            default_overwrites = news_channel.overwrites_for(self.__guild.default_role)
            default_overwrites.view_channel = False
            default_overwrites.read_messages = False
            default_overwrites.send_messages = False
            default_overwrites.read_message_history = False

            await news_channel.set_permissions(
                self.__guild.default_role,
                overwrite=default_overwrites
            )

            news_role_overwrites = news_channel.overwrites_for(news_role)
            news_role_overwrites.view_channel = True
            news_role_overwrites.read_messages = True
            news_role_overwrites.read_message_history = True

            if not self.__data["read_only"]:
                news_role_overwrites.send_messages = True

            await news_channel.set_permissions(
                news_role,
                overwrite=news_role_overwrites
            )

            news_entry = db.News.create(
                id=news_channel.id,
                guild=self.__guild.id,
                role=news_role.id,
                description=None,
                name=self.__data["name"],
            )

            command_view = instance.Instance(view_callback=news_view.View, bot_instance=self.__bot_instance)
            await command_view.create_manual(channel, self.__author, "news", data={"news_entry": news_channel.id})

            await self.__interaction.response.send_message(
                "News channel created",
                ephemeral=True
            )
        elif self.__data['subcommand'] == "remove":
            if guild_settings.news_category is None:
                await self.__interaction.response.send_message(
                    "News channel not found",
                    ephemeral=True
                )

                return

            news_entry = db.News.get_or_none(db.News.id == self.__data["news_channel"])

            if news_entry is None:
                await self.__interaction.response.send_message(
                    "News channel not found",
                    ephemeral=True
                )

                return

            news_role = self.__guild.get_role(news_entry.role)
            await news_role.delete()

            news_channel = self.__guild.get_channel(news_entry.id)
            await news_channel.delete()

            news_entry.delete_instance()

            news_entries = db.News.select().where(db.News.guild == self.__guild.id)

            if len(news_entries) == 0:
                category = self.__guild.get_channel(guild_settings.news_category)
                channel = self.__guild.get_channel(guild_settings.news_channel)

                await category.delete()
                await channel.delete()

                guild_settings.news_category = None
                guild_settings.news_channel = None
                guild_settings.save()

            await self.__interaction.response.send_message(
                "News channel removed",
                ephemeral=True
            )
        elif self.__data['subcommand'] == "description":
            await self.__interaction.response.send_modal(
                news_view.Modal(
                    self.__channel.id, self.__bot_instance, self.__guild
                )
            )
