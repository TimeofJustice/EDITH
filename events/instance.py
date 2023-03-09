import json
import nextcord

from mysql_bridge import Mysql


class Instance:
    def __init__(self, view_callback, bot_instance):
        self.__view_callback = view_callback
        self.__bot_instance = bot_instance
        self.__message = None

        self.__author = None
        self.__guild = None
        self.__channel = None
        self.__data = None

    async def create(self, user_interaction: nextcord.Interaction, title, data=None, ephemeral=False):
        self.__guild = user_interaction.guild
        self.__channel = user_interaction.channel
        self.__author = user_interaction.user

        if data is None:
            self.__data = {}
        else:
            self.__data = data

        await user_interaction.send("Loading...", ephemeral=ephemeral)
        self.__message = await user_interaction.original_message()

        mysql = Mysql()
        mysql.insert(table="instances", colms="(message_id, author_id, channel_id, guild_id, type, data)",
                     values=(self.__message.id, self.__author.id, self.__channel.id, self.__guild.id, title,
                             json.dumps(self.__data, ensure_ascii=False)))
        self.__bot_instance.add_instance(self.__message.id, self)

        message_view = self.__view_callback(self.__author, self.__guild, self.__channel, self.__message,
                                            self.__bot_instance, self.__data)
        await message_view.init()

    async def create_manual(self, text_channel: nextcord.TextChannel, author: nextcord.Member,
                            title, data=None):
        self.__guild = text_channel.guild
        self.__channel = text_channel
        self.__author = author

        if data is None:
            self.__data = {}
        else:
            self.__data = data

        self.__message = await self.__channel.send("Loading...")

        mysql = Mysql()
        mysql.insert(table="instances", colms="(message_id, author_id, channel_id, guild_id, type, data)",
                     values=(self.__message.id, self.__author.id, self.__channel.id, self.__guild.id, title,
                             json.dumps(self.__data, ensure_ascii=False)))
        self.__bot_instance.add_instance(self.__message.id, self)

        message_view = self.__view_callback(self.__author, self.__guild, self.__channel, self.__message,
                                            self.__bot_instance, self.__data)
        await message_view.init()

    async def initiate(self, instance_data):
        bot = self.__bot_instance.get_bot()
        self.__guild = bot.get_guild(instance_data["guild_id"])
        self.__channel = self.__guild.get_channel(instance_data["channel_id"])
        self.__message = await self.__channel.fetch_message(instance_data["message_id"])
        self.__author = await self.__guild.fetch_member(instance_data["author_id"])
        self.__data = json.loads(instance_data["data"])

        self.__bot_instance.add_instance(self.__message.id, self)
        message_view = self.__view_callback(self.__author, self.__guild, self.__channel, self.__message,
                                            self.__bot_instance, self.__data)
        await self.__message.edit(view=message_view)
        await message_view.init()

    async def reload(self):
        message_view = self.__view_callback(self.__author, self.__guild, self.__channel, self.__message,
                                            self.__bot_instance, self.__data)
        await message_view.init()

    def get_message_id(self):
        return self.__message.id
