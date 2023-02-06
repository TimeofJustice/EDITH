import nextcord
from mysql_bridge import Mysql


class View(nextcord.ui.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data):
        super().__init__(timeout=None)
        self.__author = author
        self.__guild = guild
        self.__channel = channel
        self.__message = message
        self.__instance_data = instance_data
        self.__mysql = Mysql()
        self.__bot_instance = bot_instance
        self.__bot = self.__bot_instance.get_bot()

    def __is_author(self, interaction: nextcord.Interaction, exception_owner=False):
        user = interaction.user
        if self.__author.id == user.id or (exception_owner and user.id == self.__bot_instance.owner_id):
            return True
        else:
            return False

    def __clean_up(self):
        for key in self.__instance_data.keys():
            self.__instance_data[key] = self.__instance_data[key].replace("'", "\"")
