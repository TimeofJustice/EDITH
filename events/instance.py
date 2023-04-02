import json
import nextcord

import db


class Instance:
    def __init__(self, view_callback, bot_instance):
        self.__view_callback = view_callback
        self.__bot_instance = bot_instance
        self.__message = None

        self.__author = None
        self.__guild = None
        self.__channel = None
        self.__data = {}

        self.__message_view = None

    async def __create_message(self, title: str):
        self.__bot_instance.create_user_profile(self.__author)
        user = db.User.get_or_none(db.User.id == self.__author.id)
        guild = db.Guild.get_or_none(db.Guild.id == self.__guild.id)
        db.Instance.create(id=self.__message.id, user=user, channel_id=self.__channel.id,
                           guild=guild, type=title, data=json.dumps(self.__data, ensure_ascii=False))
        self.__bot_instance.add_instance(self.__message.id, self)

        self.__message_view = self.__view_callback(self.__author, self.__guild, self.__channel, self.__message,
                                                   self.__bot_instance, self.__data)
        await self.__message_view.init()

    async def create(self, user_interaction: nextcord.Interaction, title, data=None, ephemeral=False):
        self.__guild = user_interaction.guild
        self.__channel = user_interaction.channel
        self.__author = user_interaction.user

        if data is not None:
            self.__data = data

        await user_interaction.send("Loading...", ephemeral=ephemeral)
        self.__message = await user_interaction.original_message()

        await self.__create_message(title)

    async def create_manual(self, text_channel: nextcord.TextChannel, author: nextcord.Member,
                            title, data=None):
        self.__guild = text_channel.guild
        self.__channel = text_channel
        self.__author = author

        if data is not None:
            self.__data = data

        self.__message = await self.__channel.send("Loading...")

        await self.__create_message(title)

    async def initiate(self, instance_data):
        bot = self.__bot_instance.get_bot()
        self.__guild = bot.get_guild(instance_data.guild.id)
        self.__channel = self.__guild.get_channel(instance_data.channel_id)
        self.__author = await self.__guild.fetch_member(instance_data.user.id)
        self.__data = json.loads(instance_data.data)

        try:
            self.__message = await self.__channel.fetch_message(instance_data.id)

            self.__bot_instance.add_instance(self.__message.id, self)
            self.__message_view = self.__view_callback(self.__author, self.__guild, self.__channel, self.__message,
                                                       self.__bot_instance, self.__data)
            await self.__message.edit(view=self.__message_view)
            await self.__message_view.init()
        except nextcord.NotFound as e:
            print(f"In '__initiate_instances' ({instance_data.id}):\n{e}\n\tRecreate Instance...")
            db.PollVote.delete().where(db.PollVote.poll_id == instance_data.id).execute()
            db.Instance.delete().where(db.Instance.id == instance_data.id).execute()
            await self.create_manual(self.__channel, self.__author, instance_data.type, self.__data)

            if instance_data.type == "config":
                scm_room = db.SCMRoom.get(db.SCMRoom.id == self.__channel.category.id)
                scm_room.instance = self.__message.id
                scm_room.save()

            return
        except Exception as e:
            print(f"In '__initiate_instances' ({instance_data.id}):\n{e}")
            db.PollVote.delete().where(db.PollVote.poll_id == instance_data.id).execute()
            db.Instance.delete().where(db.Instance.id == instance_data.id).execute()

            await self.__message.delete()

            return

    async def reload(self):
        await self.__message_view.init(reloaded=True)

    def get_message_id(self):
        return self.__message.id
