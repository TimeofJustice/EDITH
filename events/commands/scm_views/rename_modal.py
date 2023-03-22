import json

import nextcord

import db


class Modal(nextcord.ui.Modal):
    def __init__(self, room, guild, data, bot_instance):
        self.__room = room
        self.__guild = guild
        self.__data = data
        self.__bot_instance = bot_instance
        super().__init__("Smart Channel Manager")

        self.__name = nextcord.ui.TextInput(label=f"What should it be called?", style=nextcord.TextInputStyle.short,
                                            placeholder=f"Name?", required=True)
        self.add_item(self.__name)

    async def callback(self, interaction: nextcord.Interaction):
        room = db.SCMRoom.get_or_none(id=self.__room.id)

        channels = json.loads(room.channels)
        text_channel = self.__guild.get_channel(int(channels["text_channel"]))
        voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
        category = self.__room

        if self.__data["target"] == "voice":
            await voice_channel.edit(name=self.__name.value)
        elif self.__data["target"] == "text":
            await text_channel.edit(name=self.__name.value)
        elif self.__data["target"] == "category":
            await category.edit(name=self.__name.value)
