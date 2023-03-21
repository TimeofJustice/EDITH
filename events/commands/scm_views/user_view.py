import json
import nextcord

import db
from events import command, view, permissions
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__add_button = Button(label="Add", emoji="📥", row=0, args=("add",),
                                   style=nextcord.ButtonStyle.blurple, callback=self.__callback_add)
        self.__remove_button = Button(label="Remove", emoji="📤", row=0, args=("remove",),
                                      style=nextcord.ButtonStyle.blurple, callback=self.__callback_remove)

        self.__block_button = Button(label="Block", emoji="⛔", row=0, args=("block",),
                                     style=nextcord.ButtonStyle.blurple, callback=self.__callback_block)
        self.__unblock_button = Button(label="Unblock", emoji="✅", row=0, args=("unblock",),
                                       style=nextcord.ButtonStyle.blurple, callback=self.__callback_unblock)

        self.__promote_button = Button(label="Promote", emoji="⬆", row=0, args=("promote",),
                                       style=nextcord.ButtonStyle.blurple, callback=self.__callback_promote)
        self.__demote_button = Button(label="Demote", emoji="⬇", row=0, args=("demote",),
                                      style=nextcord.ButtonStyle.blurple, callback=self.__callback_demote)

        self.__cancel_button = Button(label="Cancel", emoji="❌", row=0, args=("cancel",),
                                      style=nextcord.ButtonStyle.red, callback=self.__callback_cancel)

    async def init(self, **kwargs):
        category = self.__channel.category
        target = self.__guild.get_member(int(self.__instance_data["user"]))
        user_data = self.__mysql.select(table="scm_users", colms="status",
                                        clause=f"WHERE category_id={category.id} and user_id={target.id}")

        if not target.bot and {"status": "owner"} not in user_data:
            embed = nextcord.Embed(
                description=f"What do you want to do with **{target.display_name}**?!",
                colour=nextcord.Colour.purple()
            )

            if {"status": "blocked"} in user_data:
                embed.add_field(
                    name="✅ Unblock",
                    value="Unblocks the user!",
                    inline=True
                )

                self.add_item(self.__unblock_button)
            else:
                if 0 < len(user_data):
                    embed.add_field(
                        name="📤 Remove",
                        value="Revokes access to the room!",
                        inline=True
                    )

                    self.add_item(self.__remove_button)
                else:
                    embed.add_field(
                        name="📥 Add",
                        value="Grants access to the room until the user is removes manually!",
                        inline=True
                    )

                    self.add_item(self.__add_button)

                embed.add_field(
                    name="⛔ Block",
                    value="Denied all future interactions with this room until the user gets unblocked!",
                    inline=True
                )

                self.add_item(self.__block_button)

                if {"status": "admin"} in user_data:
                    embed.add_field(
                        name="⬇ Demote",
                        value="Revokes access to the config!",
                        inline=True
                    )

                    self.add_item(self.__demote_button)
                else:
                    embed.add_field(
                        name="⬆ Promote",
                        value="Grants access to the config!",
                        inline=True
                    )

                    self.add_item(self.__promote_button)

            self.add_item(self.__cancel_button)

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            del_after = None
        elif {"status": "owner"} in user_data:
            embed = nextcord.Embed(
                description=f"This is the room from **{self.__author.display_name}**!",
                colour=nextcord.Colour.orange()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            del_after = 5
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()
        else:
            embed = nextcord.Embed(
                description=f"**{self.__author.display_name}** is a bot!",
                colour=nextcord.Colour.orange()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            del_after = 5
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

        await self.__message.edit(content="", embed=embed, view=self, delete_after=del_after)

    async def __callback_add(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            target = self.__guild.get_member(int(self.__instance_data["user"]))
            category = self.__channel.category

            room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                            clause=f"WHERE id={self.__instance_data['room_id']}")[0]

            channels = json.loads(room_data["channels"])
            text_channel = self.__guild.get_channel(int(channels["text_channel"]))
            voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
            queue_channel = self.__guild.get_channel(int(channels["queue_channel"]))

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.update({target: permissions.SCM.Text.Allowed()})
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.update({target: permissions.SCM.Voice.Allowed()})
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.update({target: permissions.SCM.Queue.Blocked()})
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{target.display_name}** can now access this room!",
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
                                values=(target.id, category.id, self.__guild.id, "invited"))
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    async def __callback_remove(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            target = self.__guild.get_member(int(self.__instance_data["user"]))
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
            config_overwrites.pop(target, None)
            await config_channel.edit(overwrites=config_overwrites)

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.pop(target, None)
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.pop(target, None)
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.pop(target, None)
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{target.display_name}** can no longer access this room!",
                colour=nextcord.Colour.red()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(content="", embed=embed, view=None, delete_after=5)

            self.__mysql.delete(table="scm_users",
                                clause=f"WHERE user_id={target.id} and category_id={category.id}")
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    async def __callback_block(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            target = self.__guild.get_member(int(self.__instance_data["user"]))
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
            config_overwrites.pop(target, None)
            await config_channel.edit(overwrites=config_overwrites)

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.update({target: permissions.SCM.Text.Blocked()})
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.update({target: permissions.SCM.Voice.Blocked()})
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.update({target: permissions.SCM.Queue.Blocked()})
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{target.display_name}** can now no longer interact with this room!",
                colour=nextcord.Colour.green()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(content="", embed=embed, view=None, delete_after=5)

            self.__mysql.delete(table="scm_users",
                                clause=f"WHERE user_id={target.id} and category_id={category.id}")
            self.__mysql.insert(table="scm_users", colms="(user_id, category_id, guild_id, status)",
                                values=(target.id, category.id, self.__guild.id, "blocked"))
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

            if target.voice.channel.category == category:
                await target.move_to(None)

        return args

    async def __callback_unblock(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            target = self.__guild.get_member(int(self.__instance_data["user"]))
            category = self.__channel.category

            room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                            clause=f"WHERE id={self.__instance_data['room_id']}")[0]

            channels = json.loads(room_data["channels"])
            config_channel = self.__guild.get_channel(int(channels["config_channel"]))
            text_channel = self.__guild.get_channel(int(channels["text_channel"]))
            voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
            queue_channel = self.__guild.get_channel(int(channels["queue_channel"]))

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.pop(target, None)
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.pop(target, None)
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.pop(target, None)
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{target.display_name}** is no longer blocked!",
                colour=nextcord.Colour.red()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(content="", embed=embed, view=None, delete_after=5)

            self.__mysql.delete(table="scm_users",
                                clause=f"WHERE user_id={target.id} and category_id={category.id} and status='blocked'")
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    async def __callback_promote(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            target = self.__guild.get_member(int(self.__instance_data["user"]))
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
            config_overwrites.update({target: permissions.SCM.Config.Allowed()})
            await config_channel.edit(overwrites=config_overwrites)

            text_overwrites = {}
            text_overwrites.update(text_channel.overwrites)
            text_overwrites.update({target: permissions.SCM.Text.Allowed()})
            await text_channel.edit(overwrites=text_overwrites)

            voice_overwrites = {}
            voice_overwrites.update(voice_channel.overwrites)
            voice_overwrites.update({target: permissions.SCM.Voice.Allowed()})
            await voice_channel.edit(overwrites=voice_overwrites)

            queue_overwrites = {}
            queue_overwrites.update(queue_channel.overwrites)
            queue_overwrites.update({target: permissions.SCM.Queue.Blocked()})
            await queue_channel.edit(overwrites=queue_overwrites)

            embed = nextcord.Embed(
                description=f"**{target.display_name}** is now admin!",
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
                                values=(target.id, category.id, self.__guild.id, "admin"))
            self.__mysql.insert(table="scm_users", colms="(user_id, category_id, guild_id, status)",
                                values=(target.id, category.id, self.__guild.id, "invited"))
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    async def __callback_demote(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            target = self.__guild.get_member(int(self.__instance_data["user"]))
            category = self.__channel.category

            room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                            clause=f"WHERE id={self.__instance_data['room_id']}")[0]

            channels = json.loads(room_data["channels"])
            config_channel = self.__guild.get_channel(int(channels["config_channel"]))

            config_overwrites = {}
            config_overwrites.update(config_channel.overwrites)
            config_overwrites.pop(target, None)
            await config_channel.edit(overwrites=config_overwrites)

            embed = nextcord.Embed(
                description=f"**{target.display_name}** is no longer an admin!",
                colour=nextcord.Colour.red()
            )

            embed.set_author(
                name="Smart Channel Manager",
                icon_url="https://images-ext-2.discordapp.net/external/"
                         "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                         "icons/small-n-flat/24/678136-shield-warning-512.png"
            )

            await self.__message.edit(content="", embed=embed, view=None, delete_after=5)

            self.__mysql.delete(table="scm_users",
                                clause=f"WHERE user_id={target.id} and category_id={category.id} and status='admin'")
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

            config_message = self.__bot_instance.get_instance(room_data["message_id"])
            await config_message.reload()

        return args

    async def __callback_cancel(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            await self.__message.delete()
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

        return args
