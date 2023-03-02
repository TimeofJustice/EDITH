import json
import random

import nextcord

from events import command, instance
from events.commands.scm_views import config_view


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["command"] == "role":
            with open('data/json/emojis.json', encoding='utf-8') as f:
                emojis = json.load(f)

            if self.__data["method"] == "add":
                role = self.__data["role"]

                role_data = self.__mysql.select(table="scm_roles", colms="id",
                                                clause=f"WHERE id={role.id}")
                role_datas = self.__mysql.select(table="scm_roles", colms="id",
                                                 clause=f"WHERE guild_id={self.__guild.id}")

                if len(role_data) == 0 and len(role_datas) < 10:
                    emoji = random.choice(emojis)

                    used_emojis = self.__mysql.select(table="scm_roles", colms="emoji",
                                                      clause=f"WHERE guild_id={self.__guild.id} and emoji='{emoji}'")

                    while {"emoji": emoji} in used_emojis:
                        emojis.remove(emoji)
                        emoji = random.choice(emojis)

                        used_emojis = self.__mysql.select(table="scm_roles", colms="emoji",
                                                          clause=f"WHERE guild_id={self.__guild.id} and emoji='{emoji}'")

                    self.__mysql.insert(table="scm_roles", colms="(id, guild_id, emoji)",
                                        values=(role.id, self.__guild.id, emoji))

                    embed = nextcord.Embed(
                        description=f"{role.mention} is now registered with the emoji `{emoji}`!",
                        colour=nextcord.Colour.green()
                    )

                    await self.__sync_roles()
                elif len(role_data) != 0:
                    embed = nextcord.Embed(
                        description=f"{role.mention} is already registered!",
                        colour=nextcord.Colour.orange()
                    )
                else:
                    embed = nextcord.Embed(
                        description=f"Maximum number of roles reached!",
                        colour=nextcord.Colour.red()
                    )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await self.__interaction.send(embed=embed, delete_after=10)
            elif self.__data["method"] == "remove":
                role = self.__data["role"]

                role_data = self.__mysql.select(table="scm_roles", colms="id",
                                                clause=f"WHERE id={role.id}")
                role_datas = self.__mysql.select(table="scm_roles", colms="id",
                                                 clause=f"WHERE guild_id={self.__guild.id}")

                if len(role_data) != 0:
                    self.__mysql.delete(table="scm_roles", clause=f"WHERE id={role.id}")

                    embed = nextcord.Embed(
                        description=f"{role.mention} is not longer registered!",
                        colour=nextcord.Colour.green()
                    )

                    await self.__sync_roles()
                else:
                    embed = nextcord.Embed(
                        description=f"{role.mention} is not registered!",
                        colour=nextcord.Colour.orange()
                    )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await self.__interaction.send(embed=embed, delete_after=10)

    async def __sync_roles(self):
        sessions = self.__mysql.select(table="instances", colms="*",
                                       clause=f"WHERE guild_id={self.__guild.id} and "
                                              f"type='config'")

        for session in sessions:
            try:
                command = instance.Instance(view_callback=config_view.View, bot_instance=self.__bot_instance)
                await command.initiate(session)
            except Exception as e:
                print(f"In '__initiate_instances' ({session['message_id']}):\n{e}")
                self.__mysql.delete(table="poll_submits", clause=f"WHERE poll_id={session['message_id']}")
                self.__mysql.delete(table="instances", clause=f"WHERE message_id={session['message_id']}")

                try:
                    guild = self.__bot.get_guild(session["guild_id"])
                    channel = guild.get_channel(session["channel_id"])
                    message = await channel.fetch_message(session["message_id"])

                    await message.delete()
                except Exception as e:
                    print(e)
