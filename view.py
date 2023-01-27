import nextcord
from mysql_bridge import Mysql


class View(nextcord.ui.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data):
        super().__init__()
        self.__author = author
        self.__guild = guild
        self.__channel = channel
        self.__message = message
        self.__instance_data = instance_data
        self.__mysql = Mysql()
        self.__bot_instance = bot_instance
