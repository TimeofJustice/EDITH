import json
import nextcord

from mysql_bridge import Mysql


class Instance:
    def __init__(self, view_callback, bot_instance):
        self.__view_callback = view_callback
        self.__bot_instance = bot_instance

    async def create(self, user_interaction: nextcord.Interaction, title, data=None, ephemeral=False):
        guild = user_interaction.guild
        channel = user_interaction.channel
        message = None
        author = user_interaction.user

        if data is None:
            data = {}

        await user_interaction.send("Loading...", ephemeral=ephemeral)
        message = await user_interaction.original_message()

        mysql = Mysql()
        mysql.insert(table="instances", colms="(message_id, author_id, channel_id, guild_id, type, data)",
                     values=(message.id, author.id, channel.id, guild.id, title, json.dumps(data)))

        message_view = self.__view_callback(author, guild, channel, message, self.__bot_instance, data)
        await message_view.init()

    async def initiate(self, instance_data):
        bot = self.__bot_instance.get_bot()
        guild = bot.get_guild(instance_data["guild_id"])
        channel = guild.get_channel(instance_data["channel_id"])
        message = await channel.fetch_message(instance_data["message_id"])
        author = await guild.fetch_member(instance_data["author_id"])
        data = json.loads(instance_data["data"])

        message_view = self.__view_callback(author, guild, channel, message, self.__bot_instance, data)
        await message.edit(view=message_view)
        await message_view.init()
