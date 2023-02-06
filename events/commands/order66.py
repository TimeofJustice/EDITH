import asyncio
import json
import random
from sys import platform

import nextcord

from events import view


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        if instance_data is None:
            instance_data = {}

        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.add_item(Button(label="❌ Stop", row=0, args=("stop",),
                             style=nextcord.ButtonStyle.red, callback=self.__callback_stop))

    async def init(self):
        guild = self.__guild

        busy_guilds = []

        for voice_client in self.__bot.voice_clients:
            busy_guilds.append(voice_client.guild.id)

        sessions = self.__mysql.select(table="instances", colms="*",
                                       clause=f"WHERE guild_id={self.__guild.id} AND type='order66'")

        if guild.id in busy_guilds or 1 < len(sessions):
            embed = nextcord.Embed(
                title="Order-66 failed!",
                description="You have failed me for the last time!\n"
                            "I am currently unavailable for more tasks!",
                colour=nextcord.Colour.orange()
            )

            embed.set_image(url="attachment://order66-2.gif")

            with open('data/pics/order66-2.gif', 'rb') as fp:
                await self.__message.edit(content="", embed=embed, view=None,
                                          file=nextcord.File(fp, 'order66-2.gif'))

            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            await asyncio.sleep(5)
            await self.__message.delete()

            return
        else:
            target_id = self.__instance_data["target"]
            target = self.__guild.get_member(target_id)

            if target.voice is None or target.bot:
                embed = nextcord.Embed(
                    title="Order-66 failed!",
                    description="You have failed me for the last time!\n"
                                "Your target is not available for the force!",
                    colour=nextcord.Colour.red()
                )

                embed.set_image(url="attachment://order66-2.gif")

                with open('data/pics/order66-2.gif', 'rb') as fp:
                    await self.__message.edit(content="", embed=embed, view=None,
                                              file=nextcord.File(fp, 'order66-2.gif'))

                self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

                await asyncio.sleep(5)
                await self.__message.delete()

                return

            if self.__instance_data.get("origin_channel") is None:
                start_channel = target.voice.channel
            else:
                start_channel = self.__guild.get_channel(self.__instance_data["origin_channel"])
                await target.move_to(start_channel)

            self.__instance_data["target"] = target.id
            self.__instance_data["origin_channel"] = start_channel.id

            self.__mysql.update(table="instances", value=f"data='{json.dumps(self.__instance_data)}'",
                                clause=f"WHERE message_id={self.__message.id}")

            embed = nextcord.Embed(
                title="Execute order-66!",
                description="Commander Cody, the time has come. Execute Order 66!",
                colour=nextcord.Colour.from_rgb(0, 0, 0)
            )

            embed.set_image(url="attachment://order66-3.gif")

            with open('data/pics/order66-3.gif', 'rb') as fp:
                await self.__message.edit(content="", embed=embed,
                                          file=nextcord.File(fp, 'order66-3.gif'), view=self)

            voice_client = await start_channel.connect()
            await guild.change_voice_state(channel=start_channel, self_deaf=True)

            if platform == "win32":
                player = nextcord.FFmpegPCMAudio(source='data/mp3/Execute_Order_66.mp3',
                                                 executable="data/drivers/ffmpeg.exe", options="-loglevel panic")
            else:
                player = nextcord.FFmpegPCMAudio(source='data/mp3/Execute_Order_66.mp3', options="-loglevel panic")
            voice_client.play(player)

            while voice_client.is_playing():
                await asyncio.sleep(.5)

            await voice_client.disconnect()

            channels = []
            custom_channel_data = self.__mysql.select("custom_channels", colms="id",
                                                      clause=" WHERE guild_id={}".format(guild.id))

            custom_channels = []
            for custom_channel in custom_channel_data:
                custom_channels.append(custom_channel[0])

            for channel in guild.voice_channels:
                if channel.permissions_for(target) and channel.permissions_for(target).connect and \
                        channel.id not in custom_channels and channel != guild.afk_channel and \
                        channel != start_channel:
                    channels.append(channel)

            next_channel = random.choice(channels)
            session = self.__mysql.select(table="instances", colms="*",
                                          clause=f"WHERE message_id={self.__message.id}")

            while target.voice is not None and len(session) != 0:
                session = self.__mysql.select(table="instances", colms="*",
                                              clause=f"WHERE message_id={self.__message.id}")

                if next_channel not in channels:
                    channels.append(next_channel)

                next_channel = random.choice(channels)

                await target.move_to(next_channel)
                channels.remove(next_channel)
                await asyncio.sleep(1.5)

            if target.voice is not None:
                await target.move_to(start_channel)

            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            await asyncio.sleep(10)

            await self.__message.delete()

    async def __callback_stop(self, interaction: nextcord.Interaction, *args):
        if self.__is_author(interaction):
            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            embed = nextcord.Embed(
                title="Order-66 stopped!",
                description="I have brought peace, freedom, justice, "
                            "\nand security to my new empire!",
                colour=nextcord.Colour.orange()
            )

            embed.set_image(url="attachment://order66-4.gif")

            with open('data/pics/order66-4.gif', 'rb') as fp:
                await self.__message.edit(content="", embed=embed, view=None, file=nextcord.File(fp, 'order66-4.gif'))

        return args


class Button(nextcord.ui.Button):
    def __init__(self, label, style, row, callback, args, disabled=False):
        self.__callback = callback
        self.__args = args
        super().__init__(label=label, style=style, row=row, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction):
        await self.__callback(interaction, self.__args)
