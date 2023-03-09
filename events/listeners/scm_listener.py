import asyncio
import json
import nextcord

import events.listener
from events import instance, permissions
from events.commands.scm_views import config_view, queue_view


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(bot_instance, data)

    async def call(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        self.__guild = member.guild

        if before.channel != after.channel:
            is_joined = before.channel is None and after.channel is not None
            is_left = before.channel is not None and after.channel is None
            is_moved = before.channel is not None and after.channel is not None

            room_datas = self.__mysql.select(table="scm_rooms", colms="id, channels")

            creator_data = self.__mysql.select(table="scm_creators", colms="*",
                                               clause=f"WHERE guild_id={self.__guild.id}")

            if 0 < len(creator_data):
                creator_data = creator_data[0]

                self.__scm_creator_room = self.__guild.get_channel(int(creator_data["id"]))
                scm_room_ids = []
                for room in room_datas:
                    scm_room_ids.append(room["id"])

                scm_queue_ids = []
                for room in room_datas:
                    channels = json.loads(room["channels"])
                    scm_queue_ids.append(channels["queue_channel"])

                if after.channel is not None and after.channel == self.__scm_creator_room:
                    await self.__create_room(member)
                elif before.channel is not None and before.channel.category is not None:
                    if before.channel.category.id in scm_room_ids:
                        if before.channel.id in scm_queue_ids:
                            await self.__left_queue(member, before.channel.category)
                        else:
                            await self.__delete_room(before.channel.category)

                if after.channel is not None and after.channel.category is not None:
                    if after.channel.category.id in scm_room_ids and after.channel.id in scm_queue_ids:
                        await self.__join_queue(member, after.channel.category)

    async def __create_room(self, member: nextcord.Member):
        config_overwrites = {
            member: permissions.SCM.Config.Allowed(),
            self.__guild.default_role: permissions.SCM.Config.Default()
        }
        text_overwrites = {
            member: permissions.SCM.Text.Allowed(),
            self.__guild.default_role: permissions.SCM.Text.Default()
        }
        voice_overwrites = {
            member: permissions.SCM.Voice.Allowed(),
            self.__guild.default_role: permissions.SCM.Voice.Default()
        }
        queue_overwrites = {
            member: permissions.SCM.Queue.Blocked(),
            self.__guild.default_role: permissions.SCM.Queue.Default()
        }

        category = await self.__guild.create_category(
            name=f"{member.name}'s Room (S.C.M)",
            position=self.__scm_creator_room.category.position
        )
        config_channel = await self.__guild.create_text_channel(
            name="Config",
            category=category,
            overwrites=config_overwrites
        )
        text_channel = await self.__guild.create_text_channel(
            name=f"{member.name}'s Chat",
            category=category,
            overwrites=text_overwrites
        )
        voice_channel = await self.__guild.create_voice_channel(
            name=f"{member.name}'s Lounge",
            category=category,
            overwrites=voice_overwrites
        )
        queue_channel = await self.__guild.create_voice_channel(
            name="Queue",
            category=category,
            overwrites=queue_overwrites
        )

        await text_channel.edit(topic="The responsibility for sent or deleted messages lies solely by the room-owner!")

        channels = {
            "config_channel": config_channel.id,
            "text_channel": text_channel.id,
            "voice_channel": voice_channel.id,
            "queue_channel": queue_channel.id,
        }

        self.__mysql.insert(table="scm_rooms", colms="(id, guild_id, channels, message_id, owner_id)",
                            values=(category.id, self.__guild.id, json.dumps(channels), 0, member.id))

        if member.voice is not None and member.voice.channel == self.__scm_creator_room:
            await member.move_to(voice_channel)

            data = {
                "room_id": category.id
            }

            command = instance.Instance(view_callback=config_view.View, bot_instance=self.__bot_instance)
            await command.create_manual(config_channel, member, "config", data=data)

            config_msg = command.get_message_id()

            await asyncio.sleep(2)

            self.__mysql.update(table="scm_rooms", value=f"message_id={config_msg}",
                                clause=f"WHERE id={category.id}")

            self.__mysql.insert(table="scm_users", colms="(user_id, category_id, guild_id, status)",
                                values=(member.id, category.id, self.__guild.id, "owner"))

            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                values=(category.id, self.__guild.id))
            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                values=(config_channel.id, self.__guild.id))
            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                values=(text_channel.id, self.__guild.id))
            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                values=(voice_channel.id, self.__guild.id))
            self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                values=(queue_channel.id, self.__guild.id))
        else:
            await self.__delete_room(category)

            return

    async def __delete_room(self, category: nextcord.CategoryChannel):
        room_data = self.__mysql.select(table="scm_rooms", colms="channels, permanent",
                                        clause=f"WHERE id={category.id}")[0]

        channels = json.loads(room_data["channels"])
        config_channel = self.__guild.get_channel(channels["config_channel"])
        text_channel = self.__guild.get_channel(channels["text_channel"])
        voice_channel = self.__guild.get_channel(channels["voice_channel"])
        queue_channel = self.__guild.get_channel(channels["queue_channel"])

        if room_data["permanent"] == 0 and len(voice_channel.members) == 0:
            await queue_channel.delete()
            await voice_channel.delete()
            await text_channel.delete()
            await config_channel.delete()
            await category.delete()

            self.__mysql.delete(table="scm_rooms", clause=f"WHERE id={category.id}")
            self.__mysql.delete(table="scm_room_roles", clause=f"WHERE category_id={category.id}")
            self.__mysql.delete(table="scm_users", clause=f"WHERE category_id={category.id}")
            self.__mysql.delete(table="instances", clause=f"WHERE channel_id={text_channel.id}")
            self.__mysql.delete(table="instances", clause=f"WHERE channel_id={config_channel.id}")

    async def __join_queue(self, member: nextcord.Member, category: nextcord.CategoryChannel):
        room_data = self.__mysql.select(table="scm_rooms", colms="channels, permanent",
                                        clause=f"WHERE id={category.id}")[0]

        channels = json.loads(room_data["channels"])
        config_channel = self.__guild.get_channel(channels["config_channel"])

        data = {
            "room_id": category.id,
            "target": member.id
        }

        command = instance.Instance(view_callback=queue_view.View, bot_instance=self.__bot_instance)
        await command.create_manual(config_channel, member, "queue", data=data)

    async def __left_queue(self, member: nextcord.Member, category: nextcord.CategoryChannel):
        instance_data = self.__mysql.select(table="instances", colms="message_id",
                                            clause=f"WHERE type='queue' AND author_id={member.id}")

        if 0 < len(instance_data):
            instance_data = instance_data[0]

            room_data = self.__mysql.select(table="scm_rooms", colms="channels, permanent",
                                            clause=f"WHERE id={category.id}")[0]
            channels = json.loads(room_data["channels"])
            config_channel = self.__guild.get_channel(channels["config_channel"])

            message = await config_channel.fetch_message(instance_data["message_id"])

            embed = nextcord.Embed(
                description=f"**{member.display_name}** has left the queue!",
                colour=nextcord.Colour.purple()
            )

            await message.edit(embed=embed, view=None, delete_after=5)
            self.__mysql.delete(table="instances", clause=f"WHERE message_id={instance_data['message_id']}")
