import asyncio
import json

import nextcord
import yt_dlp

from events import command, instance
from events.commands.music_views import play_view


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["command"] == "play":
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

                        await self.__interaction.send(embed=embed, ephemeral=True)
                        return
                else:
                    music_instance = music_instance[0]
                    instance_channel = self.__guild.get_channel(int(music_instance["channel_id"]))

                if self.__author in instance_channel.members:
                    url = self.__data["link"].replace(" ", "")

                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = "https://" + url

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
                                await command_instance.create(self.__interaction, "status",
                                                              data={"method": "play"})
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

                                await self.__interaction.send(embed=embed, ephemeral=True)
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

                        await self.__interaction.send(embed=embed, ephemeral=True)
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

                    await self.__interaction.send(embed=embed, ephemeral=True)
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

                await self.__interaction.send(embed=embed, ephemeral=True)
        if self.__data["command"] == "search":
            pass
        if self.__data["command"] == "status":
            command_instance = instance.Instance(view_callback=play_view.View, bot_instance=self.__bot_instance)
            await command_instance.create(self.__interaction, "status",
                                          data={"method": "status"})

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
