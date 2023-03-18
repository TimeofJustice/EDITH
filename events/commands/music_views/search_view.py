import asyncio
import json

import nextcord
import yt_dlp

from events import view, instance
from events.commands.music_views import play_view
from events.view import Button
from youtubesearchpython import VideosSearch


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__play_button = Button(label="Play", emoji="▶️", row=1, args=("play",),
                                    style=nextcord.ButtonStyle.green, disabled=True, callback=self.__callback_play)

        self.__cancel_button = Button(label="Cancel", emoji="❌", row=1, args=("cancel",),
                                      style=nextcord.ButtonStyle.red, callback=self.__callback_cancel)
        self.__dropdown = None
        self.__results = []
        self.__result = 0

    async def init(self, **kwargs):
        self.clear_items()

        self.__results = VideosSearch(self.__instance_data["prompt"], limit=5)
        self.__results = self.__results.result()["result"]

        results_options = [nextcord.SelectOption(
            label=self.__results[x]["title"],
            value=str(x)
        ) for x in range(0, len(self.__results))]

        self.__dropdown = Dropdown(results_options, self)
        self.add_item(self.__dropdown)
        self.add_item(self.__play_button)
        self.add_item(self.__cancel_button)

        embed = nextcord.Embed(
            description=f"These are the **results** for your **prompt**!\n"
                        f"**Select** one to play this song.",
            colour=nextcord.Colour.random()
        )

        embed.set_author(
            name="Music",
            icon_url="https://images-ext-2.discordapp.net/external/"
                     "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                     "icons/small-n-flat/24/678136-shield-warning-512.png"
        )

        await self.__message.edit(content="", embed=embed, view=self)

    async def select(self, interaction: nextcord.Interaction):
        if self.__is_author(interaction):
            self.__play_button.disabled = False
            self.remove_item(self.__dropdown)

            self.__result = int(self.__dropdown.values[0])

            title = self.__results[self.__result]["title"]

            embed = nextcord.Embed(
                description=f"You selected **{title}**!\n"
                            f"Press play to play this song.",
                colour=nextcord.Colour.random()
            )

            embed.set_author(
                name="Music",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(embed=embed, view=self)

    async def __callback_play(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            if self.__author.voice is not None:
                music_instance = self.__mysql.select(table="music_instances", colms="*",
                                                     clause=f"WHERE id={self.__guild.id}")

                if len(music_instance) == 0:
                    busy_guilds = []

                    for voice_client in self.__bot.voice_clients:
                        busy_guilds.append(voice_client.guild.id)

                    if self.__guild.id not in busy_guilds:
                        instance_channel = self.__author.voice.channel
                    else:
                        embed = nextcord.Embed(
                            description=f"I am currently unavailable for more tasks!",
                            colour=nextcord.Colour.orange()
                        )

                        embed.set_author(
                            name="Music",
                            icon_url="https://images-ext-2.discordapp.net/external/"
                                     "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                                     "icons/small-n-flat/24/678136-shield-warning-512.png"
                        )


                        self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
                        await self.__message.edit(embed=embed, view=None, delete_after=5)
                        return
                else:
                    music_instance = music_instance[0]
                    instance_channel = self.__guild.get_channel(int(music_instance["channel_id"]))

                if self.__author in instance_channel.members:
                    url = f"https://www.youtube.com/watch?v={self.__results[self.__result]['id']}"

                    ydl_opts = {
                        'quiet': True,
                        "no_warnings": True,
                        'ignoreerrors': True,
                    }

                    try:
                        yt_dl = yt_dlp.YoutubeDL(ydl_opts)
                        loop = asyncio.get_event_loop()
                        data = await loop.run_in_executor(None, lambda: yt_dl.extract_info(url, download=False))

                        if data is not None:
                            song_data = {
                                "title": data["title"],
                                "artist": data["uploader"],
                                "duration": data["duration"],
                                "thumbnail": data["thumbnail"]
                            }
                            started = await self.__play(url, instance_channel, song_data)

                            if started:
                                command_instance = instance.Instance(view_callback=play_view.View,
                                                                     bot_instance=self.__bot_instance)
                                await command_instance.create(interaction, "status",
                                                              data={"method": "play"})


                                self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
                                await self.__message.delete()
                            else:
                                queue = self.__mysql.select(table="music_songs", colms="*",
                                                            clause=f"WHERE guild_id={self.__guild.id}")

                                embed = nextcord.Embed(
                                    description=f"The song was **added** to the queue, "
                                                f"there are **{len(queue) - 1} songs** ahead!",
                                    colour=nextcord.Colour.blue()
                                )

                                embed.set_author(
                                    name="Music",
                                    icon_url="https://images-ext-2.discordapp.net/external/"
                                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                                )


                                self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
                                await self.__message.edit(embed=embed, view=None, delete_after=5)
                        else:
                            raise RuntimeError
                    except:
                        embed = nextcord.Embed(
                            description=f"This URL couldn't be processed!",
                            colour=nextcord.Colour.red()
                        )

                        embed.set_author(
                            name="Music",
                            icon_url="https://images-ext-2.discordapp.net/external/"
                                     "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                                     "icons/small-n-flat/24/678136-shield-warning-512.png"
                        )


                        self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
                        await self.__message.edit(embed=embed, view=None, delete_after=5)
                else:
                    embed = nextcord.Embed(
                        description=f"There is a music-session in another voice-channel!",
                        colour=nextcord.Colour.orange()
                    )

                    embed.set_author(
                        name="Music",
                        icon_url="https://images-ext-2.discordapp.net/external/"
                                 "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                                 "icons/small-n-flat/24/678136-shield-warning-512.png"
                    )


                    self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
                    await self.__message.edit(embed=embed, view=None, delete_after=5)
            else:
                embed = nextcord.Embed(
                    description=f"You need to be in a voice-channel!",
                    colour=nextcord.Colour.orange()
                )

                embed.set_author(
                    name="Music",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
                await self.__message.edit(embed=embed, view=None, delete_after=5)

    async def __callback_cancel(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            await self.__message.delete()
            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

        return args

    async def __play(self, link, channel: nextcord.VoiceChannel, song_data=None):
        music_instance = self.__mysql.select(table="music_instances", colms="*", clause=f"WHERE id={self.__guild.id}")
        song_uuid = self.__mysql.get_uuid(table="music_songs", colm="id")

        if len(music_instance) == 0:
            self.__mysql.insert(table="music_songs", colms="(id, url, data, guild_id, is_playing, added_by)",
                                values=(song_uuid, link, json.dumps(song_data),
                                        self.__guild.id, True, self.__author.id))
            self.__mysql.insert(table="music_instances", colms="(id, owner_id, channel_id, currently_playing)",
                                values=(self.__guild.id, self.__author.id, channel.id, song_uuid))

            return True
        else:
            self.__mysql.insert(table="music_songs", colms="(id, url, data, guild_id, is_playing, added_by)",
                                values=(song_uuid, link, json.dumps(song_data),
                                        self.__guild.id, False, self.__author.id))

            sessions = self.__mysql.select(table="instances", colms="*",
                                           clause=f"WHERE guild_id={self.__guild.id} and "
                                                  f"type='status'")

            for session in sessions:
                status_message = self.__bot_instance.get_instance(session["message_id"])
                await status_message.reload()

            return False


class Dropdown(nextcord.ui.Select):
    def __init__(self, searches, view_instance):
        self.__view_instance = view_instance
        super().__init__(placeholder=f"Select a role!", min_values=1, max_values=1, options=searches)

    async def callback(self, interaction: nextcord.Interaction):
        if 0 < len(self.values):
            await self.__view_instance.select(interaction)
