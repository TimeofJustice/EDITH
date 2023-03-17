import json
import random

import nextcord

from events import command, instance
from events.commands.scm_views import config_view, queue_view, user_view, rename_modal


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["command"] == "setup":
            creator_data = self.__mysql.select(table="scm_creators", colms="*",
                                               clause=f"WHERE guild_id={self.__guild.id}")

            if 0 < len(creator_data):
                creator_data = creator_data[0]

                if self.__data["method"] == "deactivate":
                    voice_channel = self.__guild.get_channel(int(creator_data["id"]))
                    category = voice_channel.category

                    await voice_channel.delete()
                    await category.delete()

                    self.__mysql.delete(table="scm_creators", clause=f"WHERE guild_id={self.__guild.id}")

                    embed = nextcord.Embed(
                        description=f"S.C.M is not longer active!",
                        colour=nextcord.Colour.red()
                    )
                else:
                    embed = nextcord.Embed(
                        description=f"S.C.M is already activ!",
                        colour=nextcord.Colour.orange()
                    )
            else:
                if self.__data["method"] == "activate":
                    category = await self.__guild.create_category(
                        name="Smart Channel Manager"
                    )
                    self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                        values=(category.id, self.__guild.id))
                    voice_channel = await self.__guild.create_voice_channel(
                        name="S.C.M",
                        category=category
                    )
                    self.__mysql.insert(table="custom_channels", colms="(id, guild_id)",
                                        values=(voice_channel.id, self.__guild.id))

                    self.__mysql.insert(table="scm_creators", colms="(id, guild_id)",
                                        values=(voice_channel.id, self.__guild.id))

                    embed = nextcord.Embed(
                        description=f"S.C.M is now activ!",
                        colour=nextcord.Colour.green()
                    )
                else:
                    embed = nextcord.Embed(
                        description=f"S.C.M is not activ!",
                        colour=nextcord.Colour.orange()
                    )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

            await self.__interaction.send(embed=embed, ephemeral=True)
        elif self.__data["command"] == "role":
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

                await self.__interaction.send(embed=embed, ephemeral=True)
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
        elif self.__data["command"] == "user":
            category = self.__channel.category

            if category is not None and self.__is_admin(self.__interaction):
                scm_room_channels = self.__mysql.select(table="scm_rooms", colms="channels",
                                                        clause=f"WHERE id={category.id}")

                if 0 < len(scm_room_channels):
                    command_instance = instance.Instance(view_callback=user_view.View, bot_instance=self.__bot_instance)
                    await command_instance.create(self.__interaction, "user",
                                                  data={"user": self.__data["user"].id, "room_id": category.id})
            elif category is not None and not self.__is_admin(self.__interaction):
                embed = nextcord.Embed(
                    description=f"You need to be an admin of this room to use this command!",
                    colour=nextcord.Colour.orange()
                )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await self.__interaction.send(embed=embed, ephemeral=True)
            else:
                embed = nextcord.Embed(
                    description=f"This is not a S.C.M-Room!",
                    colour=nextcord.Colour.orange()
                )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await self.__interaction.send(embed=embed, ephemeral=True)
        elif self.__data["command"] == "rename":
            category = self.__channel.category

            if category is not None and self.__is_admin(self.__interaction):
                scm_room_channels = self.__mysql.select(table="scm_rooms", colms="channels",
                                                        clause=f"WHERE id={category.id}")

                if 0 < len(scm_room_channels):
                    await self.__interaction.response.send_modal(
                        rename_modal.Modal(category, self.__guild, self.__data, self.__bot_instance)
                    )
            elif category is not None and not self.__is_admin(self.__interaction):
                embed = nextcord.Embed(
                    description=f"You need to be an admin of this room to use this command!",
                    colour=nextcord.Colour.orange()
                )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await self.__interaction.send(embed=embed, ephemeral=True)
            else:
                embed = nextcord.Embed(
                    description=f"This is not a S.C.M-Room!",
                    colour=nextcord.Colour.orange()
                )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await self.__interaction.send(embed=embed, ephemeral=True)

    def __is_admin(self, interaction):
        user = interaction.user
        room_id = self.__channel.category.id

        room_data = self.__mysql.select(table="scm_users", colms="user_id",
                                        clause=f"WHERE category_id={room_id} and (status='admin' or status='owner')")

        if {"user_id": user.id} in room_data:
            return True
        else:
            return False

    async def __sync_roles(self):
        sessions = self.__mysql.select(table="instances", colms="*",
                                       clause=f"WHERE guild_id={self.__guild.id} and "
                                              f"type='config'")

        for session in sessions:
            config_message = self.__bot_instance.get_instance(session["message_id"])
            await config_message.reload()
