import nextcord


class Command:
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        self.__interaction = interaction
        self.__author = interaction.user
        self.__guild = interaction.guild
        self.__channel = interaction.channel
        self.__bot_instance = bot_instance
        self.__data = data or {}
        self.__bot = self.__bot_instance.get_bot()
