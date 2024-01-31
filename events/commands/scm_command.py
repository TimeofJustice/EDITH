import json
import random

import nextcord

import db
from events import command, instance
from events.commands.scm_views import config_view, queue_view, user_view, rename_modal


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["command"] == "setup":
            scm_creator = db.SCMCreator.get_or_none(guild=self.__guild.id)

            if scm_creator:
                if self.__data["method"] == "deactivate":
                    voice_channel = self.__guild.get_channel(int(scm_creator.channel.id))
                    category = voice_channel.category

                    await voice_channel.delete()
                    await category.delete()

                    scm_creator.delete_instance()

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
                        name="🔨 Smart Channel Manager"
                    )
                    db.CustomChannel.create(id=category.id, guild=self.__guild.id)
                    voice_channel = await self.__guild.create_voice_channel(
                        name="🚧 Create a Channel",
                        category=category
                    )
                    db.CustomChannel.create(id=voice_channel.id, guild=self.__guild.id)

                    db.SCMCreator.create(guild=self.__guild.id, channel=voice_channel.id)

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

                role_data = db.SCMRole.get_or_none(id=role.id)
                role_datas = list(db.SCMRole.select().where(db.SCMRole.guild == self.__guild.id))

                if not role_data and len(role_datas) < 10:
                    emoji = random.choice(emojis)

                    role_with_emoji = db.SCMRole.get_or_none(guild=self.__guild.id, emoji=emoji)

                    while role_with_emoji:
                        emojis.remove(emoji)
                        emoji = random.choice(emojis)

                        role_with_emoji = db.SCMRole.get_or_none(guild=self.__guild.id, emoji=emoji)

                    db.SCMRole.create(id=role.id, guild=self.__guild.id, emoji=emoji)

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

                role_data = db.SCMRole.get_or_none(id=role.id)

                if role_data:
                    role_data.delete_instance()

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
                room = db.SCMRoom.get_or_none(id=category.id)

                if room:
                    command_instance = instance.Instance(view_callback=user_view.View, bot_instance=self.__bot_instance)
                    await command_instance.create(self.__interaction, "user",
                                                  data={"user": self.__data["user"].id, "room_id": category.id})
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
                room = db.SCMRoom.get_or_none(id=category.id)

                if room:
                    await self.__interaction.response.send_modal(
                        rename_modal.Modal(category, self.__guild, self.__data, self.__bot_instance)
                    )
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
        elif self.__data["command"] == "config":
            category = self.__channel.category

            if category is not None and self.__is_admin(self.__interaction):
                room = db.SCMRoom.get_or_none(id=category.id)

                if room:
                    session = room.instance

                    command = instance.Instance(view_callback=config_view.View, bot_instance=self.__bot_instance)
                    await command.initiate(session)

                    embed = nextcord.Embed(
                        description=f"Config is now open!",
                        colour=nextcord.Colour.green()
                    )

                    embed.set_author(
                        name="Smart Channel Manager"
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

        admin = db.SCMUser.get_or_none(user=user.id, room=room_id, status="admin")
        owner = db.SCMUser.get_or_none(user=user.id, room=room_id, status="owner")

        if admin or owner:
            return True
        else:
            return False

    async def __sync_roles(self):

        sessions = list(db.Instance.select().where(db.Instance.guild == self.__guild.id, db.Instance.type == "config"))

        for session in sessions:
            config_message = self.__bot_instance.get_instance(session.id)
            await config_message.reload()
