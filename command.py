import nextcord

from mysql_bridge import Mysql


class Command:
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data):
        self.__interaction = interaction
        self.__author = interaction.user
        self.__guild = interaction.guild
        self.__channel = interaction.channel
        self.__mysql = Mysql()
        self.__bot_instance = bot_instance
        self.__data = data
