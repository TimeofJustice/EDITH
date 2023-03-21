import json
import nextcord

import db
from events import command, view, permissions
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__add_button = Button(label="Add", emoji="📥", row=0, args=("add",),
                                   style=nextcord.ButtonStyle.green, callback=self.__callback_add)
        self.__voice_button = Button(label="Only voice", emoji="🔊", row=0, args=("voice",),
                                     style=nextcord.ButtonStyle.blurple, callback=self.__callback_voice)
        self.__block_button = Button(label="Block", emoji="⛔", row=0, args=("block",),
                                     style=nextcord.ButtonStyle.red, callback=self.__callback_block)

        self.add_item(self.__add_button)
        self.add_item(self.__voice_button)
        self.add_item(self.__block_button)

    async def init(self, **kwargs):
        embed = nextcord.Embed(
            description=f"{self.__author.display_name} is waiting!",
            colour=nextcord.Colour.purple()
        )

        embed.add_field(
            name="📥 Add",
            value="Grants access to the room until the user is removes manually!",
            inline=True
        )
        embed.add_field(
            name="🔊 Only voice",
            value="Grants access to the voice-channel until the user lefts!",
            inline=True
        )
        embed.add_field(
            name="⛔ Block",
            value="Denied all future interactions with this room until the user gets unblocked!",
            inline=True
        )

        embed.set_author(
            name="Smart Channel Manager",
            icon_url="https://images-ext-2.discordapp.net/external/"
                     "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                     "icons/small-n-flat/24/678136-shield-warning-512.png"
        )

        await self.__message.edit(content="", embed=embed, view=self)

    async def __callback_add(self, interaction: nextcord.Interaction, args):
        if self.__is_admin(interaction):
            category = self.__channel.category

            room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                            clause=f"WHERE id={self.__instance_data['room_id']}")[0]

            channels = json.loads(room_data["channels"])
            text_channel = self.__guild.get_channel(int(channels["text_channel"]))
            voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
            queue_channel = self.__guild.get_channel(int(channels["queue_channel"]))

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.update({self.__author: permissions.SCM.Text.Allowed()})
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.update({self.__author: permissions.SCM.Voice.Allowed()})
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.update({self.__author: permissions.SCM.Queue.Blocked()})
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{self.__author.display_name}** can now access this room!",
                colour=nextcord.Colour.green()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(content="", embed=embed, view=None, delete_after=5)

            self.__mysql.insert(table="scm_users", colms="(user_id, category_id, guild_id, status)",
                                values=(self.__author.id, category.id, self.__guild.id, "invited"))

            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            await self.__author.move_to(voice_channel)

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    async def __callback_voice(self, interaction: nextcord.Interaction, args):
        if self.__is_admin(interaction):
            room_data = self.__mysql.select(table="scm_rooms", colms="channels",
                                            clause=f"WHERE id={self.__instance_data['room_id']}")[0]

            channels = json.loads(room_data["channels"])

            voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))

            await self.__author.move_to(voice_channel)

            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

        return args

    async def __callback_block(self, interaction: nextcord.Interaction, args):
        if self.__is_admin(interaction):
            category = self.__channel.category

            room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                            clause=f"WHERE id={self.__instance_data['room_id']}")[0]

            channels = json.loads(room_data["channels"])
            config_channel = self.__guild.get_channel(int(channels["config_channel"]))
            text_channel = self.__guild.get_channel(int(channels["text_channel"]))
            voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
            queue_channel = self.__guild.get_channel(int(channels["queue_channel"]))

            config_overwrites = {}
            config_overwrites.update(config_channel.overwrites)
            config_overwrites.pop(self.__author, None)
            await config_channel.edit(overwrites=config_overwrites)

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.update({self.__author: permissions.SCM.Text.Blocked()})
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.update({self.__author: permissions.SCM.Voice.Blocked()})
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.update({self.__author: permissions.SCM.Queue.Blocked()})
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{self.__author.display_name}** is now blocked!",
                colour=nextcord.Colour.red()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(content="", embed=embed, view=None, delete_after=5)

            self.__mysql.insert(table="scm_users", colms="(user_id, category_id, guild_id, status)",
                                values=(self.__author.id, category.id, self.__guild.id, "blocked"))

            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            await self.__author.move_to(None)

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    def __is_admin(self, interaction):
        user = interaction.user
        room_id = self.__channel.category.id

        room_data = self.__mysql.select(table="scm_users", colms="user_id",
                                        clause=f"WHERE category_id={room_id} and (status='admin' or status='owner')")

        if {"user_id": user.id} in room_data:
            return True
        else:
            return False
