import nextcord
from colorama import Fore, Style

import db


class View(nextcord.ui.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(timeout=None)
        self.__author = author
        self.__guild = guild
        self.__channel = channel
        self.__message = message
        self.__instance_data = instance_data or {}
        self.__bot_instance = bot_instance
        self.__bot = self.__bot_instance.get_bot()

    def __is_author(self, interaction: nextcord.Interaction, exception_owner=False):
        user = interaction.user
        if self.__author.id == user.id or (exception_owner and user.id == self.__guild.owner_id):
            return True
        else:
            return False

    def __clean_up(self):
        for key in self.__instance_data.keys():
            self.__instance_data[key] = self.__instance_data[key].replace("'", "\"")

    async def on_error(self, error, item, interaction) -> None:
        if type(error) is nextcord.errors.NotFound:
            pass
        else:
            await super().on_error(error, item, interaction)

    async def on_timeout(self) -> None:
        db.Instance.delete().where(db.Instance.id==self.__message.id).execute()
        await self.__message.delete()
        print(f"{Fore.GREEN}Message ({self.__message.id}) had timeout{Style.RESET_ALL}")


class Button(nextcord.ui.Button):
    def __init__(self, label, style, row, callback, args, disabled=False, emoji=None):
        self.__callback = callback
        self.__args = args
        super().__init__(label=label, emoji=emoji, style=style, row=row, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction):
        await self.__callback(interaction, self.__args)
