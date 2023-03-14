import asyncio
import configparser
from datetime import datetime
import os
from pathlib import Path
import nextcord
from nextcord import ApplicationCheckFailure
from nextcord.ext import commands
from colorama import Style, Fore
from nextcord.ext.application_checks import has_permissions, ApplicationMissingPermissions, check, has_role

from events import instance
from events.commands import calculator_view, order66_view, profile_view, poll_view, tts_view, backup_view, \
    weather_command, purge_command, meme_command, up_command, about_command, logging_command, scm_command, movie_view, \
    settings_command
from events.commands.scm_views import queue_view, config_view, user_view

from events.listeners import on_message_listener, on_raw_message_delete_listener, on_voice_state_update_listener
from mysql_bridge import Mysql


class Bot:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        if config["DEFAULT"]["dev_mode"] == "True":
            print(f"{Fore.RED}Der Bot befindet sich im Developer Modus.{Style.RESET_ALL}")
            self.__token = config["DEFAULT"]["test_token"]
        else:
            self.__token = config["DEFAULT"]["main_token"]

        bot_intents = nextcord.Intents.all()
        self.__bot = commands.Bot(intents=bot_intents)
        self.__is_already_running = False
        self.__started_at = datetime.now()
        self.__owner_id = 243747656470495233
        self.__mysql = Mysql()
        self.__instances = {}

        self.__initiate_tables()
        self.__init_events()
        self.__init_commands()

        self.__bot.run(self.__token)

    def get_instance(self, key):
        return self.__instances.get(key)

    def add_instance(self, key, instance):
        self.__instances.update({key: instance})

    def remove_instance(self, key):
        self.__instances.pop(key)

    def get_bot(self):
        return self.__bot

    @staticmethod
    def get_version():
        result = list(Path(".").rglob("*.*"))
        dates = []
        for x in result:
            if not str(x).__contains__(".log"):
                dates.append(datetime.fromtimestamp(
                    os.path.getmtime(os.getcwd() + "/" + str(x))
                ).strftime('%Y.%m.%d'))
        dates.sort()
        dates.reverse()

        return dates[0]

    def get_running_time(self):
        current_time = datetime.now()
        dif = round((current_time - self.__started_at).total_seconds())
        if round(dif / 60) > 60:
            return str(round(dif / 60 / 60)) + " Hours"
        if round(dif) > 60:
            return str(round(dif / 60)) + " Minutes"
        else:
            return str(round(dif)) + " Seconds"

    def __initiate_tables(self):
        mysql = self.__mysql

        mysql.create_table(table="settings", colms="(id VARCHAR(255) PRIMARY KEY,"
                                                   "welcome_msg VARCHAR(255),"
                                                   "leave_msg VARCHAR(255),"
                                                   "msg_channel BIGINT(255))")
        mysql.add_colm(table="settings", colm="log_category", definition="BIGINT(255)", clause="AFTER msg_channel")
        mysql.add_colm(table="settings", colm="messages_channel", definition="BIGINT(255)", clause="AFTER log_category")
        mysql.add_colm(table="settings", colm="logging_level", definition="INT(255)",
                       clause="DEFAULT (0) AFTER messages_channel")
        mysql.add_colm(table="settings", colm="error_channel", definition="BIGINT(255)", clause="AFTER msg_channel")
        mysql.add_colm(table="settings", colm="default_role", definition="BIGINT(255)", clause="AFTER error_channel")

        mysql.create_table(table="guilds", colms="(id BIGINT(255) PRIMARY KEY,"
                                                 "settings VARCHAR(255),"
                                                 "FOREIGN KEY (settings) REFERENCES settings(id))")

        mysql.create_table(table="instances", colms="(message_id BIGINT(255) PRIMARY KEY,"
                                                    "author_id BIGINT(255) NOT NULL,"
                                                    "channel_id BIGINT(255) NOT NULL,"
                                                    "guild_id BIGINT(255) NOT NULL,"
                                                    "type VARCHAR(255) NOT NULL,"
                                                    "data TEXT)")

        mysql.create_table(table="poll_submits", colms="(id VARCHAR(255) primary key,"
                                                       "user_id BIGINT(255) not null,"
                                                       "poll_id BIGINT(255) not null,"
                                                       "FOREIGN KEY (poll_id) REFERENCES instances(message_id))")
        mysql.add_colm(table="poll_submits", colm="answer_id", definition="BIGINT(255)", clause="AFTER poll_id")

        mysql.create_table(table="custom_channels", colms="(id bigint(255) primary key,"
                                                          "guild_id bigint(255) not null)")

        mysql.create_table(table="backups", colms="(id VARCHAR(255) primary key)")
        mysql.add_colm(table="backups", colm="creator_id", definition="BIGINT(255)", clause="AFTER id")
        mysql.add_colm(table="backups", colm="guild_id", definition="BIGINT(255)", clause="AFTER creator_id")
        mysql.add_colm(table="backups", colm="data", definition="TEXT", clause="AFTER creator_id")
        mysql.add_colm(table="backups", colm="date", definition="datetime",
                       clause="DEFAULT CURRENT_TIMESTAMP AFTER data")

        mysql.create_table(table="scm_creators", colms="(id bigint(255) primary key,"
                                                       "guild_id bigint(255) not null)")

        mysql.create_table(table="scm_rooms", colms="(id bigint(255) primary key,"
                                                    "guild_id bigint(255) not null,"
                                                    "channels TEXT not null,"
                                                    "owner_id bigint(255) not null,"
                                                    "permanent tinyint(1) default 0)")
        mysql.add_colm(table="scm_rooms", colm="message_id", definition="bigint(255)", clause="AFTER owner_id")

        mysql.create_table(table="scm_roles", colms="(id bigint(255) primary key,"
                                                    "guild_id bigint(255) not null,"
                                                    "emoji varchar(255) not null)")

        mysql.create_table(table="scm_users", colms="(id bigint(255) auto_increment primary key,"
                                                    "user_id bigint(255) not null,"
                                                    "category_id bigint(255) not null,"
                                                    "guild_id bigint(255) not null,"
                                                    "status varchar(255) not null)")

        mysql.create_table(table="scm_room_roles", colms="(role_id bigint(255) not null,"
                                                         "category_id bigint(255) not null,"
                                                         "guild_id bigint(255) not null,"
                                                         "primary key (role_id, category_id))")

        mysql.create_table(table="movie_guessing", colms="(id bigint(255) auto_increment primary key,"
                                                         "user_id bigint(255) not null,"
                                                         "movie_id varchar(255) not null,"
                                                         "clues int(255) not null)")

    async def __initiate_instances(self, sessions, views):
        mysql = self.__mysql

        for guild in self.__bot.guilds:
            bot_client = guild.voice_client

            if bot_client is not None:
                await bot_client.disconnect(force=True)

        start = datetime.now()

        methods = []

        for session in sessions:
            methods.append(self.__reinit_session(session, views, mysql))

        await asyncio.gather(
            *methods
        )

        return len(sessions)

    async def __reinit_session(self, session, views, mysql):
        try:
            command = instance.Instance(view_callback=views[session["type"]], bot_instance=self)
            await command.initiate(session)
        except Exception as e:
            print(f"In '__initiate_instances' ({session['message_id']}):\n{e}")
            mysql.delete(table="poll_submits", clause=f"WHERE poll_id={session['message_id']}")
            mysql.delete(table="instances", clause=f"WHERE message_id={session['message_id']}")

            try:
                guild = self.__bot.get_guild(session["guild_id"])
                channel = guild.get_channel(session["channel_id"])
                message = await channel.fetch_message(session["message_id"])

                await message.delete()
            except Exception as e:
                print(e)

    def __init_events(self):
        bot = self.__bot
        mysql = self.__mysql

        @bot.event
        async def on_ready():
            if not self.__is_already_running:
                await self.__bot.sync_all_application_commands()

                guilds_data = mysql.select(table="guilds", colms="id")
                guild_ids = []
                __now = datetime.now()

                for guild_data in guilds_data:
                    guild_ids.append(guild_data["id"])

                print("(BOT) " + bot.user.name + " ist bereit [{}]".format(__now.strftime("%d/%m/%Y, %H:%M:%S")))
                print("(BOT) Vorhandene Guilden ({}):".format(len(bot.guilds)))
                for guild in bot.guilds:
                    print("\t- " + guild.name + "\t" + Fore.CYAN + str(guild.id) + Style.RESET_ALL)

                    if guild.id not in guild_ids:
                        uuid = mysql.get_uuid(table="settings", colm="id")
                        mysql.insert(table="settings", colms="(id)", values=(uuid,))

                        mysql.insert(table="guilds", colms="(id, settings)", values=(guild.id, uuid))

                self.__is_already_running = True

                status_index = 0

                while True:
                    status = ["Even Dead I Am The Hero", "v." + str(self.get_version()),
                              "Dev: TimeofJustice", "Running since: " + self.get_running_time()]
                    try:
                        await self.__bot.change_presence(activity=nextcord.Game(name=status[status_index]))
                    except Exception as e:
                        print(f"Exception in 'idle_handler':\n{e}")
                    status_index += 1
                    if status_index == len(status):
                        status_index = 0
                    await asyncio.sleep(60)
            else:
                print("(BOT) Reconnected")

        @bot.event
        async def on_message(message: nextcord.Message):
            listener = on_message_listener.Listener(self)
            await listener.call(message)

        @bot.event
        async def on_raw_message_delete(payload: nextcord.RawMessageDeleteEvent):
            listener = on_raw_message_delete_listener.Listener(self)
            await listener.call(payload)

        @bot.event
        async def on_voice_state_update(
                member: nextcord.Member,
                before: nextcord.VoiceState,
                after: nextcord.VoiceState
        ):
            listener = on_voice_state_update_listener.Listener(self)
            await listener.call(member, before, after)

        @bot.event
        async def on_guild_available(guild):
            sessions = mysql.select(table="instances", colms="*",
                                    clause=f"WHERE guild_id={guild.id}")
            views = {
                "calculator": calculator_view.View,
                "poll": poll_view.View,
                "profile": profile_view.View,
                "backup": backup_view.View,
                "order66": order66_view.View,
                "tts": tts_view.View,
                "queue": queue_view.View,
                "config": config_view.View,
                "movie": movie_view.View,
                "user": user_view.View
            }

            start = datetime.now()

            sessions_len = await self.__initiate_instances(sessions, views)

            print(f"{Fore.GREEN}Es wurden {sessions_len} Instanzen für {guild} in "
                  f"{(datetime.now() - start).seconds}s geladen.{Style.RESET_ALL}")

    def __init_commands(self):
        bot = self.__bot
        mysql = self.__mysql

        guilds_data = mysql.select(table="guilds", colms="id")
        guild_ids = []

        for guild_data in guilds_data:
            guild_ids.append(guild_data["id"])

        def is_me():
            def predicate(interaction: nextcord.Interaction):
                return interaction.user.id == 243747656470495233

            return check(predicate)

        @bot.slash_command(
            description="Opens an individual calculator, that supports basic mathematical equations.",
            guild_ids=guild_ids
        )
        async def calculator(
                interaction: nextcord.Interaction
        ):
            command = instance.Instance(view_callback=calculator_view.View, bot_instance=self)
            await command.create(interaction, "calculator")

        @bot.slash_command(
            description="Creates a poll with one question and an amount of answers from 1 - 4.",
            guild_ids=guild_ids
        )
        async def poll(
                interaction: nextcord.Interaction,
                number: int = nextcord.SlashOption(
                    name="amount",
                    description="Amount of answers (1-4)",
                    min_value=1,
                    max_value=4
                )
        ):
            await interaction.response.send_modal(poll_view.Modal(number, self, interaction.guild))

        @bot.slash_command(
            description="That's how the weather outside is, for you caveman!",
            guild_ids=guild_ids
        )
        async def weather(
                interaction: nextcord.Interaction,
                city: str = nextcord.SlashOption(
                    name="city",
                    description="Where should I look?"
                )
        ):
            command = weather_command.Command(interaction, self, {"city": city})
            await command.run()

        @bot.slash_command(
            description="Deletes an amount of messages",
            guild_ids=guild_ids
        )
        @has_permissions(manage_messages=True)
        async def purge(
                interaction: nextcord.Interaction,
                amount: int = nextcord.SlashOption(
                    name="amount",
                    description="Amount of messages, that should be deleted",
                    min_value=1,
                    max_value=100,
                    default=1
                )
        ):
            command = purge_command.Command(interaction, self, {"amount": amount})
            await command.run()

        @bot.slash_command(
            description="Shows a random meme from a subreddit!",
            guild_ids=guild_ids
        )
        async def meme(
                interaction: nextcord.Interaction,
                subreddit: str = nextcord.SlashOption(
                    name="subreddit",
                    description="Subreddit the meme should be from!",
                    required=False
                )
        ):
            command = meme_command.Command(interaction, self, {"subreddit": subreddit})
            await command.run()

        @bot.slash_command(
            guild_ids=guild_ids
        )
        async def faq(
                interaction: nextcord.Interaction
        ):
            pass

        @faq.subcommand(
            description="Uptime of E.D.I.T.H!"
        )
        async def up(
                interaction: nextcord.Interaction
        ):
            command = up_command.Command(interaction, self)
            await command.run()

        @faq.subcommand(
            description="About E.D.I.T.H!"
        )
        async def about(
                interaction: nextcord.Interaction
        ):
            command = about_command.Command(interaction, self)
            await command.run()

        @bot.slash_command(
            description="Executes the order-66!",
            guild_ids=guild_ids
        )
        @is_me()
        async def order66(
                interaction: nextcord.Interaction,
                target: nextcord.User = nextcord.SlashOption(
                    name="target",
                    description="Who is you target?",
                    required=True
                )
        ):
            command = instance.Instance(view_callback=order66_view.View, bot_instance=self)
            await command.create(interaction, "order66", data={"target": target.id})

        @bot.slash_command(
            description="Plays a custom phrase!",
            guild_ids=guild_ids
        )
        async def tts(
                interaction: nextcord.Interaction,
                phrase: str = nextcord.SlashOption(
                    name="phrase",
                    description="What should I say?"
                )
        ):
            command = instance.Instance(view_callback=tts_view.View, bot_instance=self)
            await command.create(interaction, "tts", data={"phrase": phrase})

        @bot.slash_command(
            description="Shows your or someone elses profile!",
            guild_ids=guild_ids
        )
        async def profile(
                interaction: nextcord.Interaction,
                user: nextcord.User = nextcord.SlashOption(
                    name="user",
                    description="From who do you want to see the profile?",
                    required=False
                )
        ):
            if user is None:
                user = interaction.user

            command = instance.Instance(view_callback=profile_view.View, bot_instance=self)
            await command.create(interaction, "profile", data={"user": user.id})

        @bot.slash_command(
            description="Opens the backup-terminal!",
            guild_ids=guild_ids
        )
        @has_permissions(administrator=True)
        async def backup(
                interaction: nextcord.Interaction
        ):
            command = instance.Instance(view_callback=backup_view.View, bot_instance=self)
            await command.create(interaction, "backup")

        @bot.slash_command(
            description="Opens a movie guessing game!",
            guild_ids=guild_ids
        )
        async def movle(
                interaction: nextcord.Interaction
        ):
            command = instance.Instance(view_callback=movie_view.View, bot_instance=self)
            await command.create(interaction, "movie")

        @bot.slash_command(
            guild_ids=guild_ids
        )
        async def scm(
                interaction: nextcord.Interaction
        ):
            pass

        @scm.subcommand(
            description="Activates or deactivates the S.C.M-System!"
        )
        @has_permissions(administrator=True)
        async def setup(
                interaction: nextcord.Interaction,
                method: str = nextcord.SlashOption(
                    name="method",
                    description="Do you want to add or remove a role?",
                    choices={"activate": "activate", "deactivate": "deactivate"},
                    required=True
                )
        ):
            command = scm_command.Command(interaction, self, {"command": "setup", "method": method})
            await command.run()

        @scm.subcommand(
            description="Adds or removes a role to the S.C.M-System!"
        )
        @has_permissions(administrator=True)
        async def role(
                interaction: nextcord.Interaction,
                method: str = nextcord.SlashOption(
                    name="method",
                    description="Do you want to add or remove a role?",
                    choices={"add": "add", "remove": "remove"},
                    required=True
                ),
                role: nextcord.Role = nextcord.SlashOption(
                    name="role",
                    description="Which role do you want to add or remove?",
                    required=True
                )
        ):
            command = scm_command.Command(interaction, self, {"command": "role", "method": method, "role": role})
            await command.run()

        @scm.subcommand(
            description="Opens the user-interface for your S.C.M-Room!"
        )
        async def user(
                interaction: nextcord.Interaction,
                target: nextcord.User = nextcord.SlashOption(
                    name="user",
                    description="Which user do you want to configure?",
                    required=True
                )
        ):
            command = scm_command.Command(interaction, self, {"command": "user", "user": target})
            await command.run()

        @scm.subcommand(
            description="Opens the rename-interface for your S.C.M-Room!"
        )
        async def rename(
                interaction: nextcord.Interaction,
                target: str = nextcord.SlashOption(
                    name="target",
                    description="What do you want to rename?",
                    choices={"voice-channel": "voice", "text-channel": "text", "category-channel": "category"},
                    required=True
                ),
        ):
            command = scm_command.Command(interaction, self, {"command": "rename", "target": target})
            await command.run()

        @bot.slash_command(
            guild_ids=guild_ids
        )
        async def settings(
                interaction: nextcord.Interaction
        ):
            pass

        @settings.subcommand(
            description="Sets the default role for new members!"
        )
        @has_permissions(administrator=True)
        async def default(
                interaction: nextcord.Interaction,
                target: nextcord.Role = nextcord.SlashOption(
                    name="role",
                    description="What should the default role be?",
                    required=True
                )
        ):
            command = settings_command.Command(interaction, self, {"command": "default", "role": target})
            await command.run()

        @settings.subcommand(
            description="Opens the notifications-interface, to set the join and leave messages!"
        )
        @has_permissions(administrator=True)
        async def notifications(
                interaction: nextcord.Interaction,
                target: nextcord.TextChannel = nextcord.SlashOption(
                    name="text-channel",
                    description="Where should the messages be posted?",
                    required=True
                )
        ):
            command = settings_command.Command(interaction, self, {"command": "notifications", "channel": target})
            await command.run()

        @settings.subcommand(
            description="Disables the default role or the notifications!"
        )
        @has_permissions(administrator=True)
        async def disable(
                interaction: nextcord.Interaction,
                method: str = nextcord.SlashOption(
                    name="method",
                    description="What do you want to disable?",
                    choices={"default role": "default", "notifications": "notifications"},
                    required=True
                ),
        ):
            command = settings_command.Command(interaction, self, {"command": "disable", "method": method})
            await command.run()

        @settings.subcommand(
            description="Shows the current settings for this guild!"
        )
        @has_permissions(administrator=True)
        async def show(
                interaction: nextcord.Interaction
        ):
            command = settings_command.Command(interaction, self, {"command": "show"})
            await command.run()

        @settings.subcommand(
            description="Activates the E.D.I.T.H. logging-tool!"
        )
        @has_permissions(administrator=True)
        async def logging(
                interaction: nextcord.Interaction,
                level: int = nextcord.SlashOption(
                    name="level",
                    description="What level of logging do you want to use?",
                    choices={"off": 0, "low": 1, "middle": 2, "high": 3, "highest": 4}
                )
        ):
            command = logging_command.Command(interaction, self, {"level": level})
            await command.run()

        @purge.error
        @logging.error
        @order66.error
        @role.error
        @setup.error
        @disable.error
        @notifications.error
        @default.error
        async def command_error(error: nextcord.Interaction, ctx):
            if type(ctx) == ApplicationMissingPermissions or type(ctx) == ApplicationCheckFailure:
                embed = nextcord.Embed(
                    color=nextcord.Colour.orange(),
                    title="**YOU SHALL NOT PASS**",
                    description="You don't have enough permission to perform this command!"
                )

                embed.set_image(url="attachment://403.png")

                with open('data/pics/403.png', 'rb') as fp:
                    await error.send(embed=embed, ephemeral=True, file=nextcord.File(fp, '403.png'))
            else:
                embed = nextcord.Embed(
                    color=nextcord.Colour.orange(),
                    title="**Unknown error**",
                    description=f"An **unknown error** occurred\n"
                                f"||{type(ctx)}||"
                )

                embed.set_image(url="attachment://unknown_error.gif")

                with open('data/pics/unknown_error.gif', 'rb') as fp:
                    await error.send(embed=embed, ephemeral=True, file=nextcord.File(fp, 'unknown_error.gif'))

                print(ctx)


client = Bot()
