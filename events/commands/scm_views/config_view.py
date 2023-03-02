import nextcord

from events import view
from events.view import Button
from mysql_bridge import Mysql


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        if instance_data is None:
            instance_data = {}

        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__add_button = Button(label="📥 Add", row=1, args=("add",),
                                   style=nextcord.ButtonStyle.green, callback=self.__callback_add)

        self.__remove_button = Button(label="📤 Remove", row=1, args=("remove",),
                                      style=nextcord.ButtonStyle.red, callback=self.__callback_remove)

        self.__type_button = Button(label="🕒 Roomtype", row=1, args=("type",),
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

        invited_str = ""

        if len(invited_users) == 0:
            invited_str = "None"
        else:
            for user in invited_users:
                invited_str += f"- {user[0].display_name}\n"

        blocked_str = ""

        if len(blocked_users) == 0:
            blocked_str = "None"
        else:
            for user in blocked_users:
                blocked_str += f"- {user[0].display_name}\n"

        admin_str = ""

        if len(admin_users) == 0:
            admin_str = "None"
        else:
            for user in admin_users:
                admin_str += f"- {user[0].display_name}\n"

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
        if self.__is_author(interaction, exception_owner=True):
            category = self.__channel.category

            if self.__dropdown.values[0] != "None":
                roles = [self.__guild.get_role(int(role_id)) for role_id in self.__dropdown.values]
                role_datas = self.__mysql.select(table="scm_room_roles", colms="role_id",
                                                 clause=f"WHERE category_id={category.id}")

                for role in roles:
                    if {"role_id": role.id} not in role_datas:
                        self.__mysql.insert(table="scm_room_roles", colms="(role_id, category_id, guild_id)",
                                            values=(role.id, category.id, self.__guild.id))

                await self.init()

        return args

    async def __callback_remove(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            category = self.__channel.category

            if self.__dropdown.values[0] != "None":
                roles = [self.__guild.get_role(int(role_id)) for role_id in self.__dropdown.values]

                for role in roles:
                    self.__mysql.delete(table="scm_room_roles",
                                        clause=f"WHERE category_id={category.id} and role_id={role.id}")

                await self.init()

        return args

    async def __callback_type(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
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
