import json
import nextcord
from events import view, permissions
from events.view import Button
from mysql_bridge import Mysql


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        if instance_data is None:
            instance_data = {}

        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__add_button = Button(label="Add", emoji="📥", row=1, args=("add",),
                                   style=nextcord.ButtonStyle.green, callback=self.__callback_add)

        self.__remove_button = Button(label="Remove", emoji="📤", row=1, args=("remove",),
                                      style=nextcord.ButtonStyle.red, callback=self.__callback_remove)

        self.__type_button = Button(label="Roomtype", emoji="🕒", row=1, args=("type",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_type)

        self.__dropdown = Dropdown(guild)

        self.add_item(self.__dropdown)

        self.add_item(self.__add_button)
        self.add_item(self.__remove_button)
        self.add_item(self.__type_button)

    async def init(self):
        category = self.__channel.category
        room_data = self.__mysql.select(table="scm_rooms", colms="*", clause=f"WHERE id={category.id}")[0]

        embed = nextcord.Embed(
            description=f"This is your config-terminal for your S.C.M-Room!",
            colour=nextcord.Colour.purple()
        )

        embed.add_field(
            name="Settings",
            value="You can press **add** or **remove** to grant a role access or revoke access!\n"
                  "You can also switch this room to a permanent room!",
            inline=False
        )

        role_datas = self.__mysql.select(table="scm_roles", colms="*", clause=f"WHERE guild_id={self.__guild.id}")
        roles = [[self.__guild.get_role(role["id"]), role["emoji"]] for role in role_datas]
        allowed_role_datas = self.__mysql.select(table="scm_room_roles", colms="*",
                                                 clause=f"WHERE category_id={category.id}")
        allowed_roles = [self.__guild.get_role(role["role_id"]) for role in allowed_role_datas]
        allowed_roles = [role for role in roles if role[0] in allowed_roles]
        removed_roles = [role for role in roles if role not in allowed_roles]

        allowed_str = ""

        if len(allowed_roles) == 0:
            allowed_str = "None"
        else:
            for role in allowed_roles:
                allowed_str += f"{role[1]} {role[0].mention}\n"

        removed_str = ""

        if len(removed_roles) == 0:
            removed_str = "None"
        else:
            for role in removed_roles:
                removed_str += f"{role[1]} {role[0].mention}\n"

        embed.add_field(
            name="Added roles",
            value=allowed_str,
            inline=True
        )
        embed.add_field(
            name="Removed roles",
            value=removed_str,
            inline=True
        )

        if room_data["permanent"] == 0:
            embed.add_field(
                name="Roomtype",
                value=f"🕒 Temporary",
                inline=True
            )
        else:
            embed.add_field(
                name="Roomtype",
                value=f"🕒 Permanent",
                inline=True
            )

        scm_users = self.__mysql.select(table="scm_users", colms="*", clause=f"WHERE category_id={category.id}")
        invited_users = []
        blocked_users = []
        admin_users = []

        for user_data in scm_users:
            user = self.__guild.get_member(int(user_data["user_id"]))

            if user is None:
                self.__mysql.delete(table="scm_users",
                                    clause=f"WHERE category_id={category.id} and user_id={user_data['user_id']}")
                continue

            if user_data["status"] == "admin":
                admin_users.append(user)
            elif user_data["status"] == "invited":
                invited_users.append(user)
            elif user_data["status"] == "blocked":
                blocked_users.append(user)

        invited_str = ""

        if len(invited_users) == 0:
            invited_str = "None"
        else:
            for user in invited_users:
                invited_str += f"- {user.display_name}\n"

        blocked_str = ""

        if len(blocked_users) == 0:
            blocked_str = "None"
        else:
            for user in blocked_users:
                blocked_str += f"- {user.display_name}\n"

        admin_str = ""

        if len(admin_users) == 0:
            admin_str = "None"
        else:
            for user in admin_users:
                admin_str += f"- {user.display_name}\n"

        embed.add_field(
            name="Invited users",
            value=invited_str,
            inline=True
        )
        embed.add_field(
            name="Blocked users",
            value=blocked_str,
            inline=True
        )

        embed.add_field(
            name="Admins",
            value=admin_str,
            inline=True
        )

        embed.add_field(
            name="Owner",
            value=f"**{self.__author.display_name}**",
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

            if 0 < len(self.__dropdown.values) and self.__dropdown.values[0] != "None":
                roles = [self.__guild.get_role(int(role_id)) for role_id in self.__dropdown.values]
                role_datas = self.__mysql.select(table="scm_room_roles", colms="role_id",
                                                 clause=f"WHERE category_id={category.id}")

                for role in roles:
                    if {"role_id": role.id} not in role_datas:
                        room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                                        clause=f"WHERE id={self.__instance_data['room_id']}")[0]

                        channels = json.loads(room_data["channels"])
                        text_channel = self.__guild.get_channel(int(channels["text_channel"]))
                        voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
                        queue_channel = self.__guild.get_channel(int(channels["queue_channel"]))

                        text_overwrites = {}
                        text_overwrites.update(text_channel.overwrites)
                        text_overwrites.update({role: permissions.SCM.Text.Allowed()})
                        await text_channel.edit(overwrites=text_overwrites)

                        voice_overwrites = {}
                        voice_overwrites.update(voice_channel.overwrites)
                        voice_overwrites.update({role: permissions.SCM.Voice.Allowed()})
                        await voice_channel.edit(overwrites=voice_overwrites)

                        queue_overwrites = {}
                        queue_overwrites.update(queue_channel.overwrites)
                        queue_overwrites.update({role: permissions.SCM.Queue.Blocked()})
                        await queue_channel.edit(overwrites=queue_overwrites)

                        self.__mysql.insert(table="scm_room_roles", colms="(role_id, category_id, guild_id)",
                                            values=(role.id, category.id, self.__guild.id))

                await self.init()

        return args

    async def __callback_remove(self, interaction: nextcord.Interaction, args):
        if self.__is_admin(interaction):
            category = self.__channel.category

            if 0 < len(self.__dropdown.values) and self.__dropdown.values[0] != "None":
                roles = [self.__guild.get_role(int(role_id)) for role_id in self.__dropdown.values]
                role_datas = self.__mysql.select(table="scm_room_roles", colms="role_id",
                                                 clause=f"WHERE category_id={category.id}")

                for role in roles:
                    if {"role_id": role.id} in role_datas:
                        room_data = self.__mysql.select(table="scm_rooms", colms="channels, message_id",
                                                        clause=f"WHERE id={self.__instance_data['room_id']}")[0]

                        channels = json.loads(room_data["channels"])
                        text_channel = self.__guild.get_channel(int(channels["text_channel"]))
                        voice_channel = self.__guild.get_channel(int(channels["voice_channel"]))
                        queue_channel = self.__guild.get_channel(int(channels["queue_channel"]))

                        text_overwrites = {}
                        text_overwrites.update(text_channel.overwrites)
                        text_overwrites.pop(role)
                        await text_channel.edit(overwrites=text_overwrites)

                        voice_overwrites = {}
                        voice_overwrites.update(voice_channel.overwrites)
                        voice_overwrites.pop(role)
                        await voice_channel.edit(overwrites=voice_overwrites)

                        queue_overwrites = {}
                        queue_overwrites.update(queue_channel.overwrites)
                        queue_overwrites.pop(role)
                        await queue_channel.edit(overwrites=queue_overwrites)

                        self.__mysql.delete(table="scm_room_roles",
                                            clause=f"WHERE category_id={category.id} and role_id={role.id}")

                await self.init()

        return args

    async def __callback_type(self, interaction: nextcord.Interaction, args):
        if self.__is_admin(interaction):
            category = self.__channel.category

            room_data = self.__mysql.select(table="scm_rooms", colms="permanent",
                                            clause=f"WHERE id={category.id}")[0]
            room_datas = self.__mysql.select(table="scm_rooms", colms="permanent",
                                             clause=f"WHERE guild_id={self.__guild.id} "
                                                    f"and owner_id={self.__author.id} "
                                                    f"and permanent=1")

            if room_data["permanent"] == 0 and len(room_datas) < 2:
                self.__mysql.update(table="scm_rooms", value="permanent=1",
                                    clause=f"WHERE id={category.id}")

                await self.init()
            elif room_data["permanent"] == 1:
                self.__mysql.update(table="scm_rooms", value="permanent=0",
                                    clause=f"WHERE id={category.id}")

                await self.init()

                await self.__delete_room(category)
            else:
                embed = nextcord.Embed(
                    description=f"You reached the limit of permanent rooms!",
                    colour=nextcord.Colour.red()
                )

                embed.set_author(
                    name="Smart Channel Manager",
                    icon_url="https://images-ext-2.discordapp.net/external/"
                             "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                             "icons/small-n-flat/24/678136-shield-warning-512.png"
                )

                await interaction.send(embed=embed, delete_after=10)

        return args

    async def __delete_room(self, category: nextcord.CategoryChannel):
        room_data = self.__mysql.select(table="scm_rooms", colms="channels, permanent",
                                        clause=f"WHERE id={category.id}")[0]

        channels = json.loads(room_data["channels"])
        config_channel = self.__guild.get_channel(channels["config_channel"])
        text_channel = self.__guild.get_channel(channels["text_channel"])
        voice_channel = self.__guild.get_channel(channels["voice_channel"])
        queue_channel = self.__guild.get_channel(channels["queue_channel"])

        if room_data["permanent"] == 0 and len(voice_channel.members) == 0:
            await queue_channel.delete()
            await voice_channel.delete()
            await text_channel.delete()
            await config_channel.delete()
            await category.delete()

            self.__mysql.delete(table="scm_rooms", clause=f"WHERE id={category.id}")
            self.__mysql.delete(table="scm_room_roles", clause=f"WHERE category_id={category.id}")
            self.__mysql.delete(table="scm_users", clause=f"WHERE category_id={category.id}")
            self.__mysql.delete(table="instances", clause=f"WHERE channel_id={text_channel.id}")
            self.__mysql.delete(table="instances", clause=f"WHERE channel_id={config_channel.id}")

    def __is_admin(self, interaction):
        user = interaction.user
        room_id = self.__channel.category.id

        room_data = self.__mysql.select(table="scm_users", colms="user_id",
                                        clause=f"WHERE category_id={room_id} and (status='admin' or status='owner')")

        if {"user_id": user.id} in room_data:
            return True
        else:
            return False


class Dropdown(nextcord.ui.Select):
    def __init__(self, guild):
        options = []

        mysql = Mysql()
        role_datas = mysql.select(table="scm_roles", colms="id, emoji", clause=f"WHERE guild_id={guild.id}")
        max_roles = 1

        if len(role_datas) == 0:
            options.append(nextcord.SelectOption(label=f"None",
                                                 value="None"))
            max_roles = 1
        else:
            for role_data in role_datas:
                role = guild.get_role(role_data["id"])

                options.append(nextcord.SelectOption(label=f"{role_data['emoji']} {role.name}",
                                                     value=f"{role.id}"))

            max_roles = len(role_datas)

        super().__init__(placeholder=f"Select a role!", min_values=1, max_values=max_roles, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        pass
