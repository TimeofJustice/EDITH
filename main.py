import asyncio
import configparser
import json
import random
from datetime import datetime
import os
from pathlib import Path
import nextcord
import schedule
from nextcord import ApplicationCheckFailure
from nextcord.ext import commands
from colorama import Style, Fore
from nextcord.ext.application_checks import has_permissions, ApplicationMissingPermissions, check, has_role

import db
from events import instance
from events.commands import weather_command, purge_command, meme_command, up_command, about_command, music_command, \
    calculator_view, poll_view
from events.commands.music_views import play_view, search_view
from events.listeners import on_guild_remove_listener, on_member_join_listener, on_member_remove_listener, \
    on_message_listener, on_raw_message_delete_listener, on_voice_state_update_listener


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
        self.__instances = {}

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

    def create_user_profile(self, member: nextcord.Member):
        user = db.User.get_or_none(db.User.id == member.id)

        if not user:
            statistics = db.User.Statistic.create()
            daily_prog = db.User.DailyProgress.create()
            weekly_prog = db.User.WeeklyProgress.create()

            db.User.create(id=member.id, daily_progress=daily_prog, weekly_progress=weekly_prog, statistics=statistics)

        self.__get_tasks()

    def __clear_dailies(self):
        users = list(db.User.select())

        for user in users:
            dailies = user.daily_tasks

            user.daily_tasks.clear()
            user.daily_progress.time_in_voice = 0
            user.daily_progress.messages_send = 0
            user.daily_progress.movies_guessed = 0

            for daily in dailies:
                daily.delete_instance()

            user.save()
            user.daily_progress.save()

        self.__get_tasks()

    def __clear_weeklies(self):
        users = list(db.User.select())

        for user in users:
            weeklies = user.weekly_tasks

            user.weekly_tasks.clear()
            user.weekly_progress.time_in_voice = 0
            user.weekly_progress.messages_send = 0
            user.weekly_progress.movies_guessed = 0

            for weekly in weeklies:
                weekly.delete_instance()

            user.save()
            user.weekly_progress.save()

        self.__get_tasks()

    def __get_tasks(self):
        users = list(db.User.select())

        for user in users:
            daily_tasks = user.daily_tasks
            weekly_tasks = user.weekly_tasks

            with open('data/json/tasks.json', encoding='utf-8') as f:
                tasks = json.load(f)

            possible_dailies = tasks["dailies"]
            possible_weeklies = tasks["weeklies"]

            if len(daily_tasks) == 0:
                for x in range(0, 2):
                    daily_task = random.choice(possible_dailies)

                    with open('data/json/movies.json', encoding='utf-8') as f:
                        levels = json.load(f)

                    guessed_movies = len(db.MovieGuess.select().where(db.MovieGuess.user == user).execute())

                    while daily_task["accomplish_type"] == "movle_game":
                        if daily_task["amount"] < (len(levels) - guessed_movies):
                            break

                        possible_dailies.remove(daily_task)
                        daily_task = random.choice(possible_dailies)

                    user.daily_tasks.add(
                        db.User.DailyTask.create(
                            description=daily_task["description"],
                            accomplish_type=daily_task["accomplish_type"],
                            amount=daily_task["amount"],
                            xp=daily_task["xp"])
                    )
                    possible_dailies.remove(daily_task)

            if len(weekly_tasks) == 0:
                for x in range(0, 2):
                    weekly_task = random.choice(possible_weeklies)

                    with open('data/json/movies.json', encoding='utf-8') as f:
                        levels = json.load(f)

                    guessed_movies = len(db.MovieGuess.select().where(db.MovieGuess.user == user).execute())

                    while weekly_task["accomplish_type"] == "movle_game":
                        if weekly_task["amount"] < (len(levels) - guessed_movies):
                            break

                        possible_weeklies.remove(weekly_task)
                        weekly_task = random.choice(possible_weeklies)

                    user.weekly_tasks.add(
                        db.User.WeeklyTask.create(
                            description=weekly_task["description"],
                            accomplish_type=weekly_task["accomplish_type"],
                            amount=weekly_task["amount"],
                            xp=weekly_task["xp"])
                    )
                    possible_weeklies.remove(weekly_task)

            user.save()

    def check_user_progress(self, member: nextcord.Member):
        user_profile = db.User.get_or_none(id=member.id)

        daily_tasks = user_profile.daily_tasks
        weekly_tasks = user_profile.weekly_tasks

        for daily_task in daily_tasks:
            progress = 0

            if daily_task.accomplish_type == "minutes_in_voice":
                progress = user_profile.daily_progress.time_in_voice
            elif daily_task.accomplish_type == "send_messages":
                progress = user_profile.daily_progress.messages_send
            elif daily_task.accomplish_type == "movle_game":
                progress = user_profile.daily_progress.movies_guessed

            if daily_task.amount <= progress and not daily_task.completed:
                daily_task.completed = True

                user_profile.xp += daily_task.xp
                user_profile.save()
                daily_task.save()

        for weekly_task in weekly_tasks:
            progress = 0

            if weekly_task.accomplish_type == "minutes_in_voice":
                progress = user_profile.weekly_progress.time_in_voice
            elif weekly_task.accomplish_type == "send_messages":
                progress = user_profile.weekly_progress.messages_send
            elif weekly_task.accomplish_type == "movle_game":
                progress = user_profile.weekly_progress.movies_guessed

            if weekly_task.amount <= progress and not weekly_task.completed:
                weekly_task.completed = True

                user_profile.xp += weekly_task.xp
                user_profile.save()
                weekly_task.save()

    async def __initiate_instances(self, sessions, views):
        for guild in self.__bot.guilds:
            bot_client = guild.voice_client

            if bot_client is not None:
                await bot_client.disconnect(force=True)

        methods = []

        for session in sessions:
            methods.append(self.__reinit_session(session, views))

        await asyncio.gather(
            *methods
        )

        return len(sessions)

    async def __reinit_session(self, session, views):
        try:
            command = instance.Instance(view_callback=views[session.type], bot_instance=self)
            await command.initiate(session)
        except Exception as e:
            print(f"In '__initiate_instances' ({session.id}):\n{e}")
            db.PollVote.delete().where(db.PollVote.poll_id == session.id).execute()
            db.Instance.delete().where(db.Instance.id == session.id).execute()

            try:
                guild = self.__bot.get_guild(session.guild.id)
                channel = guild.get_channel(session.channel_id)
                message = await channel.fetch_message(session.id)

                await message.delete()
            except Exception as e:
                print(e)

    async def __reinit_voice_sessions(self, guild: nextcord.Guild):
        voice_sessions = list(db.VoiceSession.select().where(db.VoiceSession.guild == guild.id))

        for voice_session in voice_sessions:
            member = guild.get_member(int(voice_session.user.id))

            if member is not None:
                listener = on_voice_state_update_listener.Listener(self)
                listener.init_worker_thread(member, guild)
            else:
                voice_session.delete_instance()

        return len(voice_sessions)

    async def __schedules(self):
        schedule.every().day.at("00:00").do(self.__clear_dailies).tag('daily-tasks', 'tasks')
        schedule.every().monday.at("00:00").do(self.__clear_weeklies).tag('weekly-tasks', 'tasks')

        while True:
            schedule.run_pending()
            await asyncio.sleep(1)

    def __init_events(self):
        bot = self.__bot

        @bot.event
        async def on_ready():
            if not self.__is_already_running:
                await self.__bot.sync_all_application_commands()

                guilds = list(db.Guild.select())
                guild_ids = []
                __now = datetime.now()

                for guild in guilds:
                    guild_ids.append(guild.id)

                print("(BOT) " + bot.user.name + " ist bereit [{}]".format(__now.strftime("%d/%m/%Y, %H:%M:%S")))
                print("(BOT) Vorhandene Guilden ({}):".format(len(bot.guilds)))

                for guild in bot.guilds:
                    print("\t- " + guild.name + "\t" + Fore.CYAN + str(guild.id) + Style.RESET_ALL)

                asyncio.create_task(self.__schedules())

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
            if type(message.author) is nextcord.Member:
                self.create_user_profile(message.author)

            listener = on_message_listener.Listener(self)
            await listener.call(message)

        @bot.event
        async def on_raw_message_delete(payload: nextcord.RawMessageDeleteEvent):
            listener = on_raw_message_delete_listener.Listener(self)
            await listener.call(payload)

        @bot.event
        async def on_member_join(member: nextcord.Member):
            self.create_user_profile(member)

            listener = on_member_join_listener.Listener(self)
            await listener.call(member)

        @bot.event
        async def on_member_remove(member: nextcord.Member):
            listener = on_member_remove_listener.Listener(self)
            await listener.call(member)

        @bot.event
        async def on_voice_state_update(
                member: nextcord.Member,
                before: nextcord.VoiceState,
                after: nextcord.VoiceState
        ):
            self.create_user_profile(member)

            listener = on_voice_state_update_listener.Listener(self)
            await listener.call(member, before, after)

        @bot.event
        async def on_guild_available(guild: nextcord.Guild):
            guilds = list(db.Guild.select())
            guild_ids = []

            for guild_ in guilds:
                guild_ids.append(guild_.id)

            for guild_ in bot.guilds:
                if guild_.id not in guild_ids:
                    settings = db.Guild.Setting.create()
                    db.Guild.create(id=guild_.id, settings=settings)

            sessions = list(db.Instance.select().where(db.Instance.guild == guild.id))
            #     views = {
            #         "profile": profile_view.View,
            #         "backup": backup_view.View,
            #         "order66": order66_view.View,
            #         "tts": tts_view.View,
            #         "queue": queue_view.View,
            #         "config": config_view.View,
            #         "movie": movie_view.View,
            #         "user": user_view.View
            #     }

            views = {
                "calculator": calculator_view.View,
                "poll": poll_view.View,
                "status": play_view.View,
                "search": search_view.View
            }
            start = datetime.now()

            [message_session, voice_sessions] = await asyncio.gather(
                self.__initiate_instances(sessions, views),
                self.__reinit_voice_sessions(guild)
            )

            print(f"{Fore.GREEN}Es wurden {message_session + voice_sessions} Instanzen für {guild.name} in "
                  f"{(datetime.now() - start).seconds}s geladen.{Style.RESET_ALL}")

        @bot.event
        async def on_guild_join(guild: nextcord.Guild):
            guilds = list(db.Guild.select())
            guild_ids = []

            for guild in guilds:
                guild_ids.append(guild.id)

            for guild in bot.guilds:
                if guild.id not in guild_ids:
                    settings = db.Guild.Setting.create()
                    guild = db.Guild.create(id=guild.id, settings=settings)

        @bot.event
        async def on_guild_remove(guild: nextcord.Guild):
            listener = on_guild_remove_listener.Listener(self)
            await listener.call(guild)

    def __init_commands(self):
        bot = self.__bot

        guilds = list(db.Guild.select())
        guild_ids = []

        for guild in guilds:
            guild_ids.append(guild.id)

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

        #
        #     @bot.slash_command(
        #         description="Executes the order-66!",
        #         guild_ids=guild_ids
        #     )
        #     @is_me()
        #     async def order66(
        #             interaction: nextcord.Interaction,
        #             target: nextcord.User = nextcord.SlashOption(
        #                 name="target",
        #                 description="Who is you target?",
        #                 required=True
        #             )
        #     ):
        #         command = instance.Instance(view_callback=order66_view.View, bot_instance=self)
        #         await command.create(interaction, "order66", data={"target": target.id})
        #
        #     @bot.slash_command(
        #         description="Plays a custom phrase!",
        #         guild_ids=guild_ids
        #     )
        #     async def tts(
        #             interaction: nextcord.Interaction,
        #             phrase: str = nextcord.SlashOption(
        #                 name="phrase",
        #                 description="What should I say?"
        #             )
        #     ):
        #         command = instance.Instance(view_callback=tts_view.View, bot_instance=self)
        #         await command.create(interaction, "tts", data={"phrase": phrase})
        #
        #     @bot.slash_command(
        #         description="Shows your or someone elses profile!",
        #         guild_ids=guild_ids
        #     )
        #     async def profile(
        #             interaction: nextcord.Interaction,
        #             user: nextcord.User = nextcord.SlashOption(
        #                 name="user",
        #                 description="From who do you want to see the profile?",
        #                 required=False
        #             )
        #     ):
        #         if user is None:
        #             user = interaction.user
        #
        #         command = instance.Instance(view_callback=profile_view.View, bot_instance=self)
        #         await command.create(interaction, "profile", data={"user": user.id})
        #
        #     @bot.slash_command(
        #         description="Opens the backup-terminal!",
        #         guild_ids=guild_ids
        #     )
        #     @has_permissions(administrator=True)
        #     async def backup(
        #             interaction: nextcord.Interaction
        #     ):
        #         command = instance.Instance(view_callback=backup_view.View, bot_instance=self)
        #         await command.create(interaction, "backup")
        #
        #     @bot.slash_command(
        #         description="Opens a movie guessing game!",
        #         guild_ids=guild_ids
        #     )
        #     async def movle(
        #             interaction: nextcord.Interaction
        #     ):
        #         command = instance.Instance(view_callback=movie_view.View, bot_instance=self)
        #         await command.create(interaction, "movie")

        @bot.slash_command(
            guild_ids=guild_ids
        )
        async def music(
                interaction: nextcord.Interaction
        ):
            pass

        @music.subcommand(
            description="Plays music in the voice-channel you are in!"
        )
        async def play(
                interaction: nextcord.Interaction,
                link: str = nextcord.SlashOption(
                    name="link",
                    description="What do you want to play?",
                    required=True
                )
        ):
            command = music_command.Command(interaction, self, {"command": "play", "link": link})
            await command.run()

        @music.subcommand(
            description="Searches for music to play in the voice-channel you are in!"
        )
        async def search(
                interaction: nextcord.Interaction,
                prompt: str = nextcord.SlashOption(
                    name="prompt",
                    description="What do you search?",
                    required=True
                )
        ):
            command = music_command.Command(interaction, self, {"command": "search", "prompt": prompt})
            await command.run()

        @music.subcommand(
            description="Shows whats currently playing!"
        )
        async def status(
                interaction: nextcord.Interaction
        ):
            command = music_command.Command(interaction, self, {"command": "status"})
            await command.run()
    #
    #     @bot.slash_command(
    #         guild_ids=guild_ids
    #     )
    #     async def scm(
    #             interaction: nextcord.Interaction
    #     ):
    #         pass
    #
    #     @scm.subcommand(
    #         description="Activates or deactivates the S.C.M-System!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def setup(
    #             interaction: nextcord.Interaction,
    #             method: str = nextcord.SlashOption(
    #                 name="method",
    #                 description="Do you want to add or remove a role?",
    #                 choices={"activate": "activate", "deactivate": "deactivate"},
    #                 required=True
    #             )
    #     ):
    #         command = scm_command.Command(interaction, self, {"command": "setup", "method": method})
    #         await command.run()
    #
    #     @scm.subcommand(
    #         description="Adds or removes a role to the S.C.M-System!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def role(
    #             interaction: nextcord.Interaction,
    #             method: str = nextcord.SlashOption(
    #                 name="method",
    #                 description="Do you want to add or remove a role?",
    #                 choices={"add": "add", "remove": "remove"},
    #                 required=True
    #             ),
    #             role: nextcord.Role = nextcord.SlashOption(
    #                 name="role",
    #                 description="Which role do you want to add or remove?",
    #                 required=True
    #             )
    #     ):
    #         command = scm_command.Command(interaction, self, {"command": "role", "method": method, "role": role})
    #         await command.run()
    #
    #     @scm.subcommand(
    #         description="Opens the user-interface for your S.C.M-Room!"
    #     )
    #     async def user(
    #             interaction: nextcord.Interaction,
    #             target: nextcord.User = nextcord.SlashOption(
    #                 name="user",
    #                 description="Which user do you want to configure?",
    #                 required=True
    #             )
    #     ):
    #         command = scm_command.Command(interaction, self, {"command": "user", "user": target})
    #         await command.run()
    #
    #     @scm.subcommand(
    #         description="Opens the rename-interface for your S.C.M-Room!"
    #     )
    #     async def rename(
    #             interaction: nextcord.Interaction,
    #             target: str = nextcord.SlashOption(
    #                 name="target",
    #                 description="What do you want to rename?",
    #                 choices={"voice-channel": "voice", "text-channel": "text", "category-channel": "category"},
    #                 required=True
    #             ),
    #     ):
    #         command = scm_command.Command(interaction, self, {"command": "rename", "target": target})
    #         await command.run()
    #
    #     @bot.slash_command(
    #         guild_ids=guild_ids
    #     )
    #     async def settings(
    #             interaction: nextcord.Interaction
    #     ):
    #         pass
    #
    #     @settings.subcommand(
    #         description="Sets the default role for new members!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def default(
    #             interaction: nextcord.Interaction,
    #             target: nextcord.Role = nextcord.SlashOption(
    #                 name="role",
    #                 description="What should the default role be?",
    #                 required=True
    #             )
    #     ):
    #         command = settings_command.Command(interaction, self, {"command": "default", "role": target})
    #         await command.run()
    #
    #     @settings.subcommand(
    #         description="Opens the notifications-interface, to set the join and leave messages!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def notifications(
    #             interaction: nextcord.Interaction,
    #             target: nextcord.TextChannel = nextcord.SlashOption(
    #                 name="text-channel",
    #                 description="Where should the messages be posted?",
    #                 required=True
    #             )
    #     ):
    #         command = settings_command.Command(interaction, self, {"command": "notifications", "channel": target})
    #         await command.run()
    #
    #     @settings.subcommand(
    #         description="Disables the default role or the notifications!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def disable(
    #             interaction: nextcord.Interaction,
    #             method: str = nextcord.SlashOption(
    #                 name="method",
    #                 description="What do you want to disable?",
    #                 choices={"default role": "default", "notifications": "notifications"},
    #                 required=True
    #             ),
    #     ):
    #         command = settings_command.Command(interaction, self, {"command": "disable", "method": method})
    #         await command.run()
    #
    #     @settings.subcommand(
    #         description="Shows the current settings for this guild!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def show(
    #             interaction: nextcord.Interaction
    #     ):
    #         command = settings_command.Command(interaction, self, {"command": "show"})
    #         await command.run()
    #
    #     @settings.subcommand(
    #         description="Activates the E.D.I.T.H. logging-tool!"
    #     )
    #     @has_permissions(administrator=True)
    #     async def logging(
    #             interaction: nextcord.Interaction,
    #             level: int = nextcord.SlashOption(
    #                 name="level",
    #                 description="What level of logging do you want to use?",
    #                 choices={"off": 0, "low": 1, "middle": 2, "high": 3, "highest": 4}
    #             )
    #     ):
    #         command = logging_command.Command(interaction, self, {"level": level})
    #         await command.run()

        @purge.error
        # @logging.error
        # @order66.error
        # @role.error
        # @setup.error
        # @disable.error
        # @notifications.error
        # @default.error
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
