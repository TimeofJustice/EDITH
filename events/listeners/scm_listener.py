import asyncio
import json
import random

import nextcord

import db
import events.listener
from events import instance, permissions
from events.commands.scm_views import config_view, queue_view


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

        self.__scm_creator_room = None
        self.__guild = None

    async def call(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        self.__guild = member.guild

        if before.channel != after.channel:
            is_joined = before.channel is None and after.channel is not None
            is_left = before.channel is not None and after.channel is None
            is_moved = before.channel is not None and after.channel is not None

            creator_room = db.SCMCreator.get_or_none(guild=self.__guild.id)
            rooms = db.SCMRoom.select().execute()

            if creator_room:
                self.__scm_creator_room = self.__guild.get_channel(int(creator_room.channel_id))

                scm_room_ids = []
                for room in rooms:
                    scm_room_ids.append(room.id)

                scm_queue_ids = []
                for room in rooms:
                    channels = json.loads(room.channels)
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

        with open('data/json/emojis.json', encoding='utf-8') as f:
            emojis = json.load(f)

        emoji = random.choice(emojis)

        category = await self.__guild.create_category(
            name=f"{emoji} {member.name}'s Room (S.C.M)",
            position=self.__scm_creator_room.category.position
        )
        config_channel = await self.__guild.create_text_channel(
            name="🔨 Config",
            category=category,
            overwrites=config_overwrites
        )
        text_channel = await self.__guild.create_text_channel(
            name=f"📜 {member.name}'s Chat",
            category=category,
            overwrites=text_overwrites
        )
        voice_channel = await self.__guild.create_voice_channel(
            name=f"🔈 {member.name}'s Lounge",
            category=category,
            overwrites=voice_overwrites
        )
        queue_channel = await self.__guild.create_voice_channel(
            name="⏰ Queue",
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

        scm_room = db.SCMRoom.create(id=category.id, guild=self.__guild.id, channels=json.dumps(channels),
                                     instance=0, user=member.id)

        if member.voice is not None and member.voice.channel == self.__scm_creator_room:
            await member.move_to(voice_channel)

            data = {
                "room_id": category.id
            }

            command = instance.Instance(view_callback=config_view.View, bot_instance=self.__bot_instance)
            await command.create_manual(config_channel, member, "config", data=data)

            config_msg = command.get_message_id()

            await asyncio.sleep(2)

            scm_room.instance = config_msg
            scm_room.save()

            db.SCMUser.create(user=member.id, room=category.id, guild=self.__guild.id, status="owner")

            db.CustomChannel.create(id=category.id, guild=self.__guild.id)
            db.CustomChannel.create(id=config_channel.id, guild=self.__guild.id)
            db.CustomChannel.create(id=text_channel.id, guild=self.__guild.id)
            db.CustomChannel.create(id=voice_channel.id, guild=self.__guild.id)
            db.CustomChannel.create(id=queue_channel.id, guild=self.__guild.id)
        else:
            await self.__delete_room(category)

            return

    async def __delete_room(self, category: nextcord.CategoryChannel):
        room = db.SCMRoom.get_or_none(id=category.id)

        channels = json.loads(room.channels)
        config_channel = self.__guild.get_channel(channels["config_channel"])
        text_channel = self.__guild.get_channel(channels["text_channel"])
        voice_channel = self.__guild.get_channel(channels["voice_channel"])
        queue_channel = self.__guild.get_channel(channels["queue_channel"])

        if room.is_permanent == 0 and len(voice_channel.members) == 0:
            await queue_channel.delete()
            await voice_channel.delete()
            await text_channel.delete()
            await config_channel.delete()
            await category.delete()

            db.SCMRoomRole.delete().where(db.SCMRoomRole.room == category.id).execute()
            db.SCMUser.delete().where(db.SCMUser.room == category.id).execute()
            db.SCMRoom.delete().where(db.SCMRoom.id == category.id).execute()
            db.Instance.delete().where(db.Instance.channel_id == text_channel.id).execute()
            db.Instance.delete().where(db.Instance.channel_id == config_channel.id).execute()

    async def __join_queue(self, member: nextcord.Member, category: nextcord.CategoryChannel):
        room = db.SCMRoom.get_or_none(id=category.id)

        channels = json.loads(room.channels)
        config_channel = self.__guild.get_channel(channels["config_channel"])

        data = {
            "room_id": category.id,
            "target": member.id
        }

        command = instance.Instance(view_callback=queue_view.View, bot_instance=self.__bot_instance)
        await command.create_manual(config_channel, member, "queue", data=data)

    async def __left_queue(self, member: nextcord.Member, category: nextcord.CategoryChannel):
        instance = db.Instance.get_or_none(type="queue", user=member.id)

        if instance:
            room = db.SCMRoom.get_or_none(id=category.id)
            channels = json.loads(room.channels)
            config_channel = self.__guild.get_channel(channels["config_channel"])

            message = await config_channel.fetch_message(instance.id)

            embed = nextcord.Embed(
                description=f"**{member.display_name}** has left the queue!",
                colour=nextcord.Colour.purple()
            )

            await message.edit(embed=embed, view=None, delete_after=5)
            instance.delete_instance()
