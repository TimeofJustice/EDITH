import asyncio
import json
from datetime import timedelta
from sys import platform

from gtts import gTTS
from langdetect import detect

import nextcord

import db
from events import view, permissions
from events.view import Button
import yt_dlp


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__vote_skip = []
        self.__vote_stop = []
        self.__vote_pause_play = []

        self.__is_paused = False
        self.__is_skipped = False
        self.__is_stopped = False

        self.__voice_client = None
        self.__radio = None

        self.__music_instance = db.MusicInstance.get_or_none(guild=self.__guild.id)
        self.__voice_channel = self.__guild.get_channel(int(self.__music_instance.channel_id))

        self.__play_button = Button(label="Play", emoji="▶️", row=0, args=("play",),
                                    style=nextcord.ButtonStyle.blurple, callback=self.__play_callback)
        self.__pause_button = Button(label="Pause", emoji="⏸️", row=0, args=("pause",),
                                     style=nextcord.ButtonStyle.blurple, callback=self.__pause_callback)
        self.__skip_button = Button(label="Skip", emoji="⏩", row=0, args=("skip",),
                                    style=nextcord.ButtonStyle.green, callback=self.__skip_callback)
        self.__stop_button = Button(label="Stop", emoji="⏹️", row=0, args=("stop",),
                                    style=nextcord.ButtonStyle.red, callback=self.__stop_callback)

        self.clear_items()
        self.add_item(self.__pause_button)
        self.add_item(self.__skip_button)
        self.add_item(self.__stop_button)

    async def init(self, reloaded=False):
        await self.__update_embed()

        if self.__instance_data["method"] == "play" and not reloaded:
            self.__voice_client = await self.__voice_channel.connect()

            self.__radio = asyncio.create_task(self.__play_song())

    async def __play_song(self):
        ydl_opts = {
            'format': 'bestaudio/worst',
            "ffmpeg_location": "data/drivers/ffmpeg.exe",
            'noplaylist': True,
            'ignoreerrors': True,
            'quiet': True,
            'nocheckcertificate': True,
            'buffersize': 16000
        }
        music_instance = db.MusicInstance.get_or_none(guild=self.__guild.id)
        current_song = music_instance.currently_playing

        yt_dl = yt_dlp.YoutubeDL(ydl_opts)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yt_dl.extract_info(current_song.url, download=False))

        if data is not None:
            if 'entries' in data:
                data = data['entries'][0]
            filename = data['url']

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel panic -nostats'
            }

            text = data["title"]
            lang = detect(text)

            try:
                output = gTTS(text=text, lang=lang, slow=False)
                output.save("data/mp3/{}_next_song.mp3".format(self.__guild.id))
            except:
                output = gTTS(text=text, lang="en", slow=False)
                output.save("data/mp3/{}_next_song.mp3".format(self.__guild.id))

            if platform == "win32":
                player = nextcord.FFmpegPCMAudio("data/mp3/{}_next_song.mp3".format(self.__guild.id),
                                                 executable="data/drivers/ffmpeg.exe",
                                                 options="-loglevel panic")
            else:
                player = nextcord.FFmpegPCMAudio("data/mp3/{}_next_song.mp3".format(self.__guild.id),
                                                 options="-loglevel panic")

            self.__voice_client.play(player)

            while self.__voice_client.is_playing() or self.__is_paused:
                await asyncio.sleep(1)

                if self.__is_stopped:
                    return

                if self.__is_skipped:
                    self.__voice_client.stop()
                    break

                if self.__is_paused:
                    self.__voice_client.pause()
                else:
                    self.__voice_client.resume()

            if platform == "win32":
                player = nextcord.FFmpegPCMAudio(filename,
                                                 executable="data/drivers/ffmpeg.exe", options="-loglevel panic",
                                                 **ffmpeg_options)
            else:
                player = nextcord.FFmpegPCMAudio(filename, options="-loglevel panic", **ffmpeg_options)

            self.__voice_client.play(player)

            while self.__voice_client.is_playing() or self.__is_paused:
                await asyncio.sleep(1)

                if self.__is_stopped:
                    return

                if self.__is_skipped:
                    self.__voice_client.stop()
                    break

                if self.__is_paused:
                    self.__voice_client.pause()
                else:
                    self.__voice_client.resume()

            if not self.__is_skipped:
                next_song_exists = await self.__skip()
            else:
                next_song_exists = True

            self.__is_skipped = False

            if next_song_exists:
                self.__is_paused = False
                await self.__update_embed()
                await self.__play_song()

    async def __update_embed(self):
        music_instance = db.MusicInstance.get_or_none(guild=self.__guild.id)
        current_song = music_instance.currently_playing
        songs_in_queue = list(db.MusicSong.select().where(
            db.MusicSong.id != current_song.id
        ).order_by(db.MusicSong.added_at))
        next_song = songs_in_queue[0] if len(songs_in_queue) != 0 else None

        embed = nextcord.Embed(
            description=f"This is the music-terminal!",
            colour=nextcord.Colour.random()
        )

        if current_song:
            added_by = self.__guild.get_member(int(current_song.added_by.id))
            song_data = json.loads(current_song.data)
            td = timedelta(seconds=song_data['duration'])

            embed.add_field(
                name="Playing",
                value=f"**Title:** {song_data['title']}\n"
                      f"**Artist:** {song_data['artist']}\n"
                      f"**Duration:** {td}\n"
                      f"**Added by:** {added_by.display_name}",
                inline=True
            )

            embed.set_thumbnail(url=song_data["thumbnail"])

        if next_song:
            added_by = self.__guild.get_member(int(next_song.added_by.id))
            song_data = json.loads(next_song.data)
            td = timedelta(seconds=song_data['duration'])

            embed.add_field(
                name="Next",
                value=f"**Title:** {song_data['title']}\n"
                      f"**Artist:** {song_data['artist']}\n"
                      f"**Duration:** {td}\n"
                      f"**Added by:** {added_by.display_name}",
                inline=True
            )

        embed.add_field(
            name="Queue",
            value=f"There are **{len(songs_in_queue)} songs** in the queue",
            inline=False
        )

        embed.add_field(
            name="Votes",
            value=f"**Pause/Play:** {len(self.__vote_pause_play)}\n"
                  f"**Skip:** {len(self.__vote_skip)}\n"
                  f"**Stop:** {len(self.__vote_stop)}",
            inline=True
        )

        embed.set_author(
            name="Music",
            icon_url="https://images-ext-2.discordapp.net/external/"
                     "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                     "icons/small-n-flat/24/678136-shield-warning-512.png"
        )

        await self.__message.edit(content="", embed=embed, view=self)

    async def __play_callback(self, interaction: nextcord.Interaction, args):
        if self.__is_instance_owner(interaction=interaction, exception_owner=True):
            self.__play()
        else:
            if interaction.user not in self.__vote_pause_play:
                self.__vote_pause_play.append(interaction.user)

            if (len(self.__voice_channel.members) - 1) / 2 <= len(self.__vote_pause_play):
                self.__play()

        await self.__update_embed()

    def __play(self):
        self.__vote_pause_play = []

        self.clear_items()
        self.add_item(self.__pause_button)
        self.add_item(self.__skip_button)
        self.add_item(self.__stop_button)

        self.__is_paused = False

    async def __pause_callback(self, interaction: nextcord.Interaction, args):
        if self.__is_instance_owner(interaction=interaction, exception_owner=True):
            self.__pause()
        else:
            if interaction.user not in self.__vote_pause_play:
                self.__vote_pause_play.append(interaction.user)

            if (len(self.__voice_channel.members) - 1) / 2 <= len(self.__vote_pause_play):
                self.__pause()

        await self.__update_embed()

    def __pause(self):
        self.__vote_pause_play = []

        self.clear_items()
        self.add_item(self.__play_button)
        self.add_item(self.__skip_button)
        self.add_item(self.__stop_button)

        self.__is_paused = True

    async def __skip_callback(self, interaction: nextcord.Interaction, args):
        if self.__is_instance_owner(interaction=interaction, exception_owner=True):
            await self.__skip()
        else:
            if interaction.user not in self.__vote_skip:
                self.__vote_skip.append(interaction.user)

            if (len(self.__voice_channel.members) - 1) / 2 <= len(self.__vote_skip):
                await self.__skip()

        await self.__update_embed()

    async def __skip(self):
        music_instance = db.MusicInstance.get_or_none(guild=self.__guild.id)
        current_song = music_instance.currently_playing

        songs_in_queue = list(db.MusicSong.select().where(
            db.MusicSong.id != current_song.id
        ).order_by(db.MusicSong.added_at))
        next_song = songs_in_queue[0] if len(songs_in_queue) != 0 else None

        self.__vote_skip = []

        if next_song is not None:
            music_instance.currently_playing = next_song
            music_instance.save()

            current_song.delete_instance()

            self.clear_items()
            self.add_item(self.__pause_button)
            self.add_item(self.__skip_button)
            self.add_item(self.__stop_button)

            self.__is_skipped = True

            return True
        else:
            await self.__stop()

            return False

    async def __stop_callback(self, interaction: nextcord.Interaction, args):
        if self.__is_instance_owner(interaction=interaction, exception_owner=True):
            await self.__stop()
        else:
            if interaction.user not in self.__vote_stop:
                self.__vote_stop.append(interaction.user)

            if (len(self.__voice_channel.members) - 1) / 2 <= len(self.__vote_stop):
                await self.__stop()

            await self.__update_embed()

    async def __stop(self):
        db.Instance.delete().where(db.Instance.id == self.__message.id).execute()
        db.MusicInstance.delete().where(db.MusicInstance.guild == self.__guild.id).execute()
        db.MusicSong.delete().where(db.MusicSong.guild == self.__guild.id).execute()

        self.__is_stopped = True

        await self.__message.delete()
        await self.__voice_client.disconnect()

    def __is_instance_owner(self, interaction: nextcord.Interaction, exception_owner=False):
        user = interaction.user
        if self.__music_instance.user.id == user.id or (exception_owner and user.id == self.__guild.owner_id):
            return True
        else:
            return False
