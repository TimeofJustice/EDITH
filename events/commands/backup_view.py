import json

import nextcord
import requests

import db
from events import view
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__create_button = Button(label="Create", emoji="⭐", row=0, args=("create",),
                                      style=nextcord.ButtonStyle.green, callback=self.__callback_create)
        self.__load_button = Button(label="Load", emoji="📤", row=0, args=("load",),
                                    style=nextcord.ButtonStyle.blurple, callback=self.__callback_load)
        self.__accept_button = None
        self.__cancel_button = Button(label="Cancel", emoji="❌", row=0, args=("cancel",),
                                      style=nextcord.ButtonStyle.red, callback=self.__callback_cancel)

        self.add_item(self.__create_button)
        self.add_item(self.__load_button)
        self.add_item(self.__cancel_button)

    async def init(self, **kwargs):
        author = self.__author

        embed = nextcord.Embed(
            title=f"Backup-Tool",
            description=f"Do you want to **create** or **load** a backup?",
            colour=nextcord.Colour.blurple()
        )
        embed.set_footer(text="ㅤ" * 22)
        await self.__message.edit(content="", embed=embed, view=self)

    async def __callback_create(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.clear_items()
            self.add_item(self.__cancel_button)

            self.__create_backup()

            embed = nextcord.Embed(
                description=f"Backup created successfully!",
                colour=nextcord.Colour.green()
            )
            embed.set_author(name="Backup-Tool",
                             icon_url="https://images-ext-2.discordapp.net/external/"
                                      "NU9I3Vhi79KV6srTXLJuHxOgiyzmEwgS5nFAbA13_YQ/https/cdn0.iconfinder.com/data/icons/"
                                      "small-n-flat/24/678134-sign-check-512.png")

            await self.__message.edit(content="", embed=embed, view=None, delete_after=30)
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

    def __create_backup(self):
        custom_channel_data = list(db.CustomChannel.select().where(db.CustomChannel.guild == self.__guild.id))

        custom_channels = []
        for custom_channel in custom_channel_data:
            custom_channels.append(custom_channel["id"])

        data = {
            "main": {
                "guild_name": self.__guild.name,
                "guild_icon": str(self.__guild.icon).replace(".webp", ".png"),
                "afk_timeout": self.__guild.afk_timeout,
                "afk_channel": str(self.__guild.afk_channel),
                "mfa_level": self.__guild.mfa_level,
                "verification_level": json.dumps(self.__guild.verification_level),
                "explicit_content_filter": json.dumps(self.__guild.explicit_content_filter),
                "default_notifications": json.dumps(self.__guild.default_notifications),
                "system_channel": str(self.__guild.system_channel)
            },
            "roles": [],
            "categories": [],
            "text_channels": [],
            "voice_channels": []
        }

        for role in self.__guild.roles:
            if not role.managed:
                data["roles"].append({
                    "name": role.name,
                    "position": role.position,
                    "mentionable": role.mentionable,
                    "color": str(role.colour),
                    "perms": dict(role.permissions),
                    "hoist": role.hoist
                })

        for category in self.__guild.categories:
            if category.id not in custom_channels:
                perms = {}

                for x in category.overwrites.keys():
                    perms.update({x.name: dict(category.overwrites[x])})

                data["categories"].append({
                    "name": category.name,
                    "position": category.position,
                    "nsfw": category.is_nsfw(),
                    "perms": perms
                })

        for text_channel in self.__guild.text_channels:
            if text_channel.id not in custom_channels:
                if text_channel.category is not None:
                    cat = text_channel.category.name
                    cat_pos = text_channel.category.position
                else:
                    cat = None
                    cat_pos = None

                perms = {}

                for x in text_channel.overwrites.keys():
                    perms.update({x.name: dict(text_channel.overwrites[x])})

                data["text_channels"].append({
                    "name": text_channel.name,
                    "position": text_channel.position,
                    "category": cat,
                    "cat_pos": cat_pos,
                    "topic": text_channel.topic,
                    "delay": text_channel.slowmode_delay,
                    "nsfw": text_channel.is_nsfw(),
                    "news": text_channel.is_news(),
                    "perms": perms,
                    "synced": text_channel.permissions_synced
                })

        for voice_channel in self.__guild.voice_channels:
            if voice_channel.id not in custom_channels:
                if voice_channel.category is not None:
                    cat = voice_channel.category.name
                    cat_pos = voice_channel.category.position
                else:
                    cat = None
                    cat_pos = None

                perms = {}

                for x in voice_channel.overwrites.keys():
                    perms.update({x.name: dict(voice_channel.overwrites[x])})

                data["voice_channels"].append({
                    "name": voice_channel.name,
                    "position": voice_channel.position,
                    "category": cat,
                    "cat_pos": cat_pos,
                    "bitrate": voice_channel.bitrate,
                    "limit": voice_channel.user_limit,
                    "perms": perms,
                    "synced": voice_channel.permissions_synced
                })

        db.Backup.create(user=self.__author.id, guild=self.__guild.id, data=json.dumps(data, ensure_ascii=False))

    async def __callback_load(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.clear_items()

            backups = list(db.Backup.select().where(db.Backup.user == self.__author.id).order_by(db.Backup.date))

            options = []
            for backup in backups:
                guild = self.__bot.get_guild(int(backup.guild.id))

                options.append(nextcord.SelectOption(label=f"{backup.date} ({guild.name})", value=backup.id))

            if 0 == len(backups):
                embed = nextcord.Embed(
                    title=f"Backup-Tool",
                    description=f"You dont have any backups!",
                    colour=nextcord.Colour.orange()
                )

                await self.__message.edit(content="", embed=embed, view=None, delete_after=5)
                db.Instance.delete().where(db.Instance.id == self.__message.id).execute()
                return

            self.__select = StringSelect(row=0, args=("input",), callback=self.__callback_select,
                                         options=options)

            self.add_item(self.__select)

            self.__cancel_button.row = 1

            self.add_item(self.__cancel_button)

            embed = nextcord.Embed(
                title=f"Backup-Tool",
                description=f"Which backup do you want to **load**?",
                colour=nextcord.Colour.blurple()
            )
            embed.set_footer(text="ㅤ" * 22)

            await self.__message.edit(content="", embed=embed, view=self)

    async def __callback_select(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.clear_items()

            self.__accept_button = Button(label="✅ Accept", row=0, args=(self.__select.values[0],),
                                          style=nextcord.ButtonStyle.green, callback=self.__load_backup)

            self.add_item(self.__accept_button)

            self.__cancel_button.row = 0

            self.add_item(self.__cancel_button)

            embed = nextcord.Embed(
                title=f"Warning",
                description=f"Are you sure, that you want to load this backup?\n"
                            f"All channels and roles will be **permanently** deleted!",
                colour=nextcord.Colour.blurple()
            )
            embed.set_author(name="Backup-Tool",
                             icon_url="https://images-ext-2.discordapp.net/external/"
                                      "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                                      "icons/small-n-flat/24/678136-shield-warning-512.png")
            embed.set_footer(text="ㅤ" * 22)

            await self.__message.edit(content="", embed=embed, view=self)

    async def __load_backup(self, interaction: nextcord.Interaction, args):
        backup_id = args[0]

        backup = db.Backup.get_or_none(id=backup_id)
        data = json.loads(backup.data)

        await self.__message.delete()
        db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

        await self.__clean_guild()

        roles = data["roles"]
        roles.reverse()

        for role in roles:
            if role["name"] != "@everyone":
                h = role["color"].lstrip('#')
                h = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

                await self.__guild.create_role(
                    name=role["name"],
                    color=nextcord.Colour.from_rgb(h[0], h[1], h[2]),
                    hoist=role["hoist"],
                    mentionable=role["mentionable"],
                    permissions=nextcord.Permissions(
                        create_instant_invite=role["perms"]["create_instant_invite"],
                        kick_members=role["perms"]["kick_members"],
                        ban_members=role["perms"]["ban_members"],
                        administrator=role["perms"]["administrator"],
                        manage_channels=role["perms"]["manage_channels"],
                        manage_guild=role["perms"]["manage_guild"],
                        add_reactions=role["perms"]["add_reactions"],
                        view_audit_log=role["perms"]["view_audit_log"],
                        priority_speaker=role["perms"]["priority_speaker"],
                        stream=role["perms"]["stream"],
                        read_messages=role["perms"]["read_messages"],
                        send_messages=role["perms"]["send_messages"],
                        send_tts_messages=role["perms"]["send_tts_messages"],
                        manage_messages=role["perms"]["manage_messages"],
                        embed_links=role["perms"]["embed_links"],
                        attach_files=role["perms"]["attach_files"],
                        read_message_history=role["perms"]["read_message_history"],
                        mention_everyone=role["perms"]["mention_everyone"],
                        external_emojis=role["perms"]["external_emojis"],
                        view_guild_insights=role["perms"]["view_guild_insights"],
                        connect=role["perms"]["connect"],
                        speak=role["perms"]["speak"],
                        mute_members=role["perms"]["mute_members"],
                        deafen_members=role["perms"]["deafen_members"],
                        move_members=role["perms"]["move_members"],
                        use_voice_activation=role["perms"]["use_voice_activation"],
                        change_nickname=role["perms"]["change_nickname"],
                        manage_nicknames=role["perms"]["manage_nicknames"],
                        manage_roles=role["perms"]["manage_roles"],
                        manage_webhooks=role["perms"]["manage_webhooks"],
                        manage_emojis=role["perms"]["manage_emojis"]
                    )
                )
            else:
                await self.__guild.default_role.edit(
                    permissions=nextcord.Permissions(
                        create_instant_invite=role["perms"]["create_instant_invite"],
                        kick_members=role["perms"]["kick_members"],
                        ban_members=role["perms"]["ban_members"],
                        administrator=role["perms"]["administrator"],
                        manage_channels=role["perms"]["manage_channels"],
                        manage_guild=role["perms"]["manage_guild"],
                        add_reactions=role["perms"]["add_reactions"],
                        view_audit_log=role["perms"]["view_audit_log"],
                        priority_speaker=role["perms"]["priority_speaker"],
                        stream=role["perms"]["stream"],
                        read_messages=role["perms"]["read_messages"],
                        send_messages=role["perms"]["send_messages"],
                        send_tts_messages=role["perms"]["send_tts_messages"],
                        manage_messages=role["perms"]["manage_messages"],
                        embed_links=role["perms"]["embed_links"],
                        attach_files=role["perms"]["attach_files"],
                        read_message_history=role["perms"]["read_message_history"],
                        mention_everyone=role["perms"]["mention_everyone"],
                        external_emojis=role["perms"]["external_emojis"],
                        view_guild_insights=role["perms"]["view_guild_insights"],
                        connect=role["perms"]["connect"],
                        speak=role["perms"]["speak"],
                        mute_members=role["perms"]["mute_members"],
                        deafen_members=role["perms"]["deafen_members"],
                        move_members=role["perms"]["move_members"],
                        use_voice_activation=role["perms"]["use_voice_activation"],
                        change_nickname=role["perms"]["change_nickname"],
                        manage_nicknames=role["perms"]["manage_nicknames"],
                        manage_roles=role["perms"]["manage_roles"],
                        manage_webhooks=role["perms"]["manage_webhooks"],
                        manage_emojis=role["perms"]["manage_emojis"]
                    )
                )

        for cat in data["categories"]:
            perms = {}

            for r_m in cat["perms"].keys():
                act_role = None
                for role in self.__guild.roles:
                    if role.name == r_m:
                        act_role = role

                if act_role is None:
                    continue

                perms.update({act_role: nextcord.PermissionOverwrite(
                    use_voice_activation=cat["perms"][r_m]["use_voice_activation"],
                    deafen_members=cat["perms"][r_m]["deafen_members"],
                    create_instant_invite=cat["perms"][r_m]["create_instant_invite"],
                    priority_speaker=cat["perms"][r_m]["priority_speaker"],
                    view_audit_log=cat["perms"][r_m]["view_audit_log"],
                    speak=cat["perms"][r_m]["speak"],
                    manage_nicknames=cat["perms"][r_m]["manage_nicknames"],
                    mention_everyone=cat["perms"][r_m]["mention_everyone"],
                    manage_guild=cat["perms"][r_m]["manage_guild"],
                    manage_roles=cat["perms"][r_m]["manage_roles"],
                    manage_channels=cat["perms"][r_m]["manage_channels"],
                    change_nickname=cat["perms"][r_m]["change_nickname"],
                    external_emojis=cat["perms"][r_m]["external_emojis"],
                    administrator=cat["perms"][r_m]["administrator"],
                    manage_emojis=cat["perms"][r_m]["manage_emojis"],
                    add_reactions=cat["perms"][r_m]["add_reactions"],
                    send_messages=cat["perms"][r_m]["send_messages"],
                    attach_files=cat["perms"][r_m]["attach_files"],
                    view_guild_insights=cat["perms"][r_m]["view_guild_insights"],
                    manage_messages=cat["perms"][r_m]["manage_messages"],
                    move_members=cat["perms"][r_m]["move_members"],
                    kick_members=cat["perms"][r_m]["kick_members"],
                    read_messages=cat["perms"][r_m]["read_messages"],
                    embed_links=cat["perms"][r_m]["embed_links"],
                    ban_members=cat["perms"][r_m]["ban_members"],
                    stream=cat["perms"][r_m]["stream"],
                    connect=cat["perms"][r_m]["connect"],
                    manage_webhooks=cat["perms"][r_m]["manage_webhooks"],
                    mute_members=cat["perms"][r_m]["mute_members"],
                    read_message_history=cat["perms"][r_m]["read_message_history"],
                    send_tts_messages=cat["perms"][r_m]["send_tts_messages"]
                )})

            await self.__guild.create_category(
                name=cat["name"],
                overwrites=perms
            )

        for voice_c in data["voice_channels"]:
            category = None

            for cat in self.__guild.categories:
                if cat.name == voice_c["category"]:
                    category = cat
                    break

            new_c = await self.__guild.create_voice_channel(
                name=voice_c["name"],
                category=category,
                bitrate=voice_c["bitrate"],
                user_limit=voice_c["limit"]
            )

            perms = {}

            for r_m in voice_c["perms"].keys():
                act_role = None
                for role in self.__guild.roles:
                    if role.name == r_m:
                        act_role = role

                if act_role is None:
                    continue

                perms.update({act_role: nextcord.PermissionOverwrite(
                    create_instant_invite=voice_c["perms"][r_m]["create_instant_invite"],
                    kick_members=voice_c["perms"][r_m]["kick_members"],
                    ban_members=voice_c["perms"][r_m]["ban_members"],
                    administrator=voice_c["perms"][r_m]["administrator"],
                    manage_channels=voice_c["perms"][r_m]["manage_channels"],
                    manage_guild=voice_c["perms"][r_m]["manage_guild"],
                    add_reactions=voice_c["perms"][r_m]["add_reactions"],
                    view_audit_log=voice_c["perms"][r_m]["view_audit_log"],
                    priority_speaker=voice_c["perms"][r_m]["priority_speaker"],
                    stream=voice_c["perms"][r_m]["stream"],
                    read_messages=voice_c["perms"][r_m]["read_messages"],
                    send_messages=voice_c["perms"][r_m]["send_messages"],
                    send_tts_messages=voice_c["perms"][r_m]["send_tts_messages"],
                    manage_messages=voice_c["perms"][r_m]["manage_messages"],
                    embed_links=voice_c["perms"][r_m]["embed_links"],
                    attach_files=voice_c["perms"][r_m]["attach_files"],
                    read_message_history=voice_c["perms"][r_m]["read_message_history"],
                    mention_everyone=voice_c["perms"][r_m]["mention_everyone"],
                    external_emojis=voice_c["perms"][r_m]["external_emojis"],
                    view_guild_insights=voice_c["perms"][r_m]["view_guild_insights"],
                    connect=voice_c["perms"][r_m]["connect"],
                    speak=voice_c["perms"][r_m]["speak"],
                    mute_members=voice_c["perms"][r_m]["mute_members"],
                    deafen_members=voice_c["perms"][r_m]["deafen_members"],
                    move_members=voice_c["perms"][r_m]["move_members"],
                    use_voice_activation=voice_c["perms"][r_m]["use_voice_activation"],
                    change_nickname=voice_c["perms"][r_m]["change_nickname"],
                    manage_nicknames=voice_c["perms"][r_m]["manage_nicknames"],
                    manage_roles=voice_c["perms"][r_m]["manage_roles"],
                    manage_webhooks=voice_c["perms"][r_m]["manage_webhooks"],
                    manage_emojis=voice_c["perms"][r_m]["manage_emojis"]
                )})

            await new_c.edit(
                sync_permissions=voice_c["synced"],
                overwrites=perms
            )

        for text_c in data["text_channels"]:
            category = None

            for cat in self.__guild.categories:
                if cat.name == text_c["category"]:
                    category = cat
                    break

            new_c = await self.__guild.create_text_channel(
                name=text_c["name"],
                category=category,
                topic=text_c["topic"],
                slowmode_delay=text_c["delay"],
                nsfw=text_c["nsfw"]
            )

            perms = {}

            for r_m in text_c["perms"].keys():
                act_role = None
                for role in self.__guild.roles:
                    if role.name == r_m:
                        act_role = role

                if act_role is None:
                    continue

                perms.update({act_role: nextcord.PermissionOverwrite(
                    create_instant_invite=text_c["perms"][r_m]["create_instant_invite"],
                    kick_members=text_c["perms"][r_m]["kick_members"],
                    ban_members=text_c["perms"][r_m]["ban_members"],
                    administrator=text_c["perms"][r_m]["administrator"],
                    manage_channels=text_c["perms"][r_m]["manage_channels"],
                    manage_guild=text_c["perms"][r_m]["manage_guild"],
                    add_reactions=text_c["perms"][r_m]["add_reactions"],
                    view_audit_log=text_c["perms"][r_m]["view_audit_log"],
                    priority_speaker=text_c["perms"][r_m]["priority_speaker"],
                    stream=text_c["perms"][r_m]["stream"],
                    read_messages=text_c["perms"][r_m]["read_messages"],
                    send_messages=text_c["perms"][r_m]["send_messages"],
                    send_tts_messages=text_c["perms"][r_m]["send_tts_messages"],
                    manage_messages=text_c["perms"][r_m]["manage_messages"],
                    embed_links=text_c["perms"][r_m]["embed_links"],
                    attach_files=text_c["perms"][r_m]["attach_files"],
                    read_message_history=text_c["perms"][r_m]["read_message_history"],
                    mention_everyone=text_c["perms"][r_m]["mention_everyone"],
                    external_emojis=text_c["perms"][r_m]["external_emojis"],
                    view_guild_insights=text_c["perms"][r_m]["view_guild_insights"],
                    connect=text_c["perms"][r_m]["connect"],
                    speak=text_c["perms"][r_m]["speak"],
                    mute_members=text_c["perms"][r_m]["mute_members"],
                    deafen_members=text_c["perms"][r_m]["deafen_members"],
                    move_members=text_c["perms"][r_m]["move_members"],
                    use_voice_activation=text_c["perms"][r_m]["use_voice_activation"],
                    change_nickname=text_c["perms"][r_m]["change_nickname"],
                    manage_nicknames=text_c["perms"][r_m]["manage_nicknames"],
                    manage_roles=text_c["perms"][r_m]["manage_roles"],
                    manage_webhooks=text_c["perms"][r_m]["manage_webhooks"],
                    manage_emojis=text_c["perms"][r_m]["manage_emojis"]
                )})

            await new_c.edit(
                sync_permissions=text_c["synced"],
                overwrites=perms
            )

        icon = requests.get(data["main"]["guild_icon"]).content

        afk_c = None
        sys_c = None

        for channel in self.__guild.channels:
            if str(channel) == data["main"]["afk_channel"]:
                afk_c = channel
            if str(channel) == data["main"]["system_channel"]:
                sys_c = channel

        await self.__guild.edit(
            name=data["main"]["guild_name"],
            icon=icon,
            afk_timeout=data["main"]["afk_timeout"],
            afk_channel=afk_c,
            verification_level=nextcord.VerificationLevel(
                int(data["main"]["verification_level"])),
            default_notifications=nextcord.NotificationLevel(
                int(data["main"]["default_notifications"])),
            explicit_content_filter=nextcord.ContentFilter(
                int(data["main"]["explicit_content_filter"])),
            system_channel=sys_c
        )

    async def __clean_guild(self):
        await self.__guild.edit(name="Loading...")

        db.CustomChannel.delete().where(db.CustomChannel.guild == self.__guild.id).execute()
        db.Instance.delete().where(db.Instance.guild == self.__guild.id).execute()
        db.SCMCreator.delete().where(db.SCMCreator.guild == self.__guild.id).execute()
        db.SCMRole.delete().where(db.SCMRole.guild == self.__guild.id).execute()
        rooms = list(db.SCMRoom.select().where(db.SCMRoom.guild == self.__guild.id))
        db.SCMRoom.delete().where(db.SCMRoom.guild == self.__guild.id).execute()
        db.SCMUser.delete().where(db.SCMUser.guild == self.__guild.id).execute()

        for room in rooms:
            db.SCMRoomRole.delete().where(db.SCMRoomRole.room == room.id).execute()

        guild = db.Guild.get_or_none(id=self.__guild.id)
        guild.settings.msg_channel = None
        guild.settings.default_role = None
        guild.settings.save()

        for role in self.__guild.roles:
            try:
                if role.name != "@everyone":
                    await role.delete()
            except Exception as e:
                str(e) + ""

        for channel in self.__guild.channels:
            await channel.delete()

        for cat in self.__guild.categories:
            await cat.delete()

    async def __callback_cancel(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            await self.__message.delete()
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

        return args


class StringSelect(nextcord.ui.StringSelect):
    def __init__(self, options, row, callback, args):
        self.__callback = callback
        self.__args = args
        super().__init__(options=options, row=row)

    async def callback(self, interaction: nextcord.Interaction):
        await self.__callback(interaction, self.__args)
