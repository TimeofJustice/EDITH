import asyncio
import json

import nextcord

import events.listener


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

            self.__scm_creator_room = self.__guild.get_channel(1073662406577881178)
            scm_voice_ids = ()
            scm_queue_ids = ()

            if (is_joined or is_moved) and after.channel == self.__scm_creator_room:
                await self.__create_room(member)
            elif before.channel is not None:
                if (is_left or is_moved) and before.channel.id in scm_voice_ids:
                    print("Delete SCM")
                elif (is_left or is_moved) and before.channel.id in scm_queue_ids:
                    print("Left Queue")
            elif (is_joined or is_moved) and after.channel.id in scm_queue_ids:
                print("Joined Queue")

    async def __create_room(self, member: nextcord.Member):
        category = await self.__guild.create_category(
            name=f"{member.name}'s Room (S.C.M)",
            position=self.__scm_creator_room.category.position
        )
        config_channel = await self.__guild.create_text_channel(
            name="Config",
            category=category
        )
        text_channel = await self.__guild.create_text_channel(
            name=f"{member.name}'s Chat",
            category=category
        )
        voice_channel = await self.__guild.create_voice_channel(
            name=f"{member.name}'s Lounge",
            category=category
        )
        queue_channel = await self.__guild.create_voice_channel(
            name="Queue",
            category=category
        )

        await text_channel.edit(topic="The responsibility for sent or deleted messages lies solely by the room-owner!")

        channels = {
            "config_channel": config_channel.id,
            "text_channel": text_channel.id,
            "voice_channel": voice_channel.id,
            "queue_channel": queue_channel.id,
        }

        if member.voice is not None and member.voice.channel == self.__scm_creator_room:
            await member.move_to(voice_channel)

            embed = nextcord.Embed(
                description="You can use `/scm config` to open the config-dialogue!",
                colour=nextcord.Colour.yellow()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            config_msg = await config_channel.send(embed=embed)

            await asyncio.sleep(2)

            if len(voice_channel.members) == 0:
                await queue_channel.delete()
                await voice_channel.delete()
                await text_channel.delete()
                await config_channel.delete()
                await category.delete()

                return

            self.__mysql.insert(table="scm_rooms", colms="(id, guild_id, channels, owner_id)",
                                values=(category.id, self.__guild.id, json.dumps(channels), member.id))

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
            await queue_channel.delete()
            await voice_channel.delete()
            await text_channel.delete()
            await config_channel.delete()
            await category.delete()

            return
