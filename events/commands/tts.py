import asyncio
import json
from platform import platform
from sys import platform
from gtts import gTTS
from langdetect import detect, DetectorFactory, detect_langs
import nextcord

from events import command, view


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
                                       clause=f"WHERE guild_id={self.__guild.id} AND type='tts'")

        if guild.id in busy_guilds or 1 < len(sessions):
            embed = nextcord.Embed(
                title="TTS failed!",
                description="I am currently unavailable for more tasks!",
                colour=nextcord.Colour.orange()
            )

            await self.__message.edit(content="", embed=embed, view=None)

            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            await asyncio.sleep(5)
            await self.__message.delete()

            return
        else:
            if self.__author.voice is None:
                embed = nextcord.Embed(
                    title="TTS failed!",
                    description="You have to be in a voice-channel!",
                    colour=nextcord.Colour.red()
                )

                await self.__message.edit(content="", embed=embed, view=None)

                self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

                await asyncio.sleep(5)
                await self.__message.delete()

                return

            if self.__instance_data.get("channel") is None:
                channel = self.__author.voice.channel
            else:
                channel = self.__guild.get_channel(self.__instance_data["origin_channel"])

            self.__clean_up()
            self.__mysql.update(table="instances",
                                value=f"data='{json.dumps(self.__instance_data, ensure_ascii=False)}'",
                                clause=f"WHERE message_id={self.__message.id}")

            embed = nextcord.Embed(
                title="Execute TTS! (Detect language...)",
                description="Can I speak to your manager please!",
                colour=nextcord.Colour.from_rgb(0, 0, 0)
            )

            await self.__message.edit(content="", embed=embed, view=self)

            voice_client = await channel.connect()
            await guild.change_voice_state(channel=channel, self_deaf=True)

            DetectorFactory.seed = 0

            text = self.__instance_data["phrase"].ljust(3, ' ')
            langs = detect_langs(text)

            if langs[0].prob < 0.8:
                lang_str = "en"
            else:
                lang_str = langs[0].lang

            embed = nextcord.Embed(
                title=f"Execute TTS! (Generate audio..., language: {lang_str})",
                description="Can I speak to your manager please!",
                colour=nextcord.Colour.from_rgb(0, 0, 0)
            )

            await self.__message.edit(content="", embed=embed, view=self)

            try:
                output = gTTS(text=text, lang=lang_str, slow=False)
                output.save("data/mp3/{}_tts.mp3".format(guild.id))
            except:
                output = gTTS(text=text, lang="en", slow=False)
                output.save("data/mp3/{}_tts.mp3".format(guild.id))

            embed = nextcord.Embed(
                title=f"Execute TTS!",
                description="Can I speak to your manager please!",
                colour=nextcord.Colour.from_rgb(0, 0, 0)
            )

            await self.__message.edit(content="", embed=embed, view=self)

            if platform == "win32":
                player = nextcord.FFmpegPCMAudio("data/mp3/{}_tts.mp3".format(guild.id),
                                                 executable="drivers/ffmpeg.exe", options="-loglevel panic")
            else:
                player = nextcord.FFmpegPCMAudio("data/mp3/{}_tts.mp3".format(guild.id), options="-loglevel panic")
            voice_client.play(player)

            session = self.__mysql.select(table="instances", colms="*",
                                          clause=f"WHERE message_id={self.__message.id}")

            while voice_client.is_playing() and len(session) != 0:
                session = self.__mysql.select(table="instances", colms="*",
                                              clause=f"WHERE message_id={self.__message.id}")
                await asyncio.sleep(.5)

            await voice_client.disconnect()

            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            await self.__message.delete()

    async def __callback_stop(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            embed = nextcord.Embed(
                title="TTS stopped!",
                description="See you next time!",
                colour=nextcord.Colour.orange()
            )

            await self.__message.edit(content="", embed=embed, view=None)

        return args


class Button(nextcord.ui.Button):
    def __init__(self, label, style, row, callback, args, disabled=False):
        self.__callback = callback
        self.__args = args
        super().__init__(label=label, style=style, row=row, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction):
        await self.__callback(interaction, self.__args)
