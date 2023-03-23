import asyncio
import configparser
import json
import random
from datetime import datetime
import os
from pathlib import Path
from typing import List

import nextcord
import schedule
from nextcord import ApplicationCheckFailure
from nextcord.ext import commands
from colorama import Style, Fore
from nextcord.ext.application_checks import has_permissions, ApplicationMissingPermissions, check, has_role

import db
from events import instance
from events.commands import weather_command, purge_command, meme_command, up_command, about_command, music_command, \
    calculator_view, poll_view, backup_view, profile_view, tts_view, movie_view, scm_command, order66_view, \
    logging_command, settings_command, animal_command
from events.commands.music_views import play_view, search_view
from events.commands.scm_views import config_view, queue_view, user_view
from events.instance import Instance
from events.listeners import on_guild_remove_listener, on_member_join_listener, on_member_remove_listener, \
    on_message_listener, on_raw_message_delete_listener, on_voice_state_update_listener


class Bot:
    """
    A class representing a bot instance.
    """

    def __init__(self):
        self.__setup_config()
        self.__setup_bot()

    def __setup_config(self):
        """
        Set up the bot configuration.
        """
        config = configparser.ConfigParser()
        config.read('data/config.ini')

        dev_mode = config["DEFAULT"]["dev_mode"] == "True"
        self.__token = config["DEFAULT"]["test_token"] if dev_mode else config["DEFAULT"]["main_token"]

        if dev_mode:
            print(f"{Fore.RED}Der Bot befindet sich im Developer Modus.{Style.RESET_ALL}")

        self.__owner_id = 243747656470495233

    def __setup_bot(self):
        """
        Set up the bot instance.
        """
        bot_intents = nextcord.Intents.all()
        self.__bot = commands.Bot(intents=bot_intents)
        self.__is_already_running = False
        self.__started_at = datetime.now()
        self.__instances = {}

        self.__init_events()
        self.__init_commands()

        self.__bot.run(self.__token)

    def get_instance(self, key: str) -> Instance:
        """
        Get an instance by key.

        :param key: The key of the instance.
        :return: The instance.
        """
        return self.__instances.get(key)

    def add_instance(self, key: str, instance: Instance):
        """
        Add an instance to the bot.

        :param key: The key of the instance.
        :param instance: The instance to add.
        """
        self.__instances[key] = instance

    def remove_instance(self, key: str):
        """
        Remove an instance from the bot.

        :param key: The key of the instance to remove.
        """
        if key in self.__instances:
            del self.__instances[key]

    def get_bot(self):
        """
        Get the bot instance.

        :return: The bot instance.
        """
        return self.__bot

    @staticmethod
    def get_version() -> str:
        """
        Get the latest version of the bot.

        :return: The latest version of the bot.
        """
        files = [f for f in Path(".").rglob("*.*") if not str(f).endswith(".log")]
        dates = [datetime.fromtimestamp(os.path.getmtime(str(f))).strftime('%Y.%m.%d') for f in files]
        return sorted(dates, reverse=True)[0]

    def get_running_time(self) -> str:
        """
        Get the running time of the bot.

        :return: The running time of the bot.
        """
        current_time = datetime.now()
        dif = round((current_time - self.__started_at).total_seconds())

        hours = dif // 3600
        minutes = (dif % 3600) // 60
        seconds = dif % 60

        if hours:
            return f"{hours} {'Hour' if hours == 1 else 'Hours'}"
        elif minutes:
            return f"{minutes} {'Minute' if minutes == 1 else 'Minutes'}"
        else:
            return f"{seconds} {'Second' if seconds == 1 else 'Seconds'}"

    def create_user_profile(self, member: nextcord.Member):
        """
        Creates a user profile for the given member if it doesn't already exist.

        :param member: A discord.Member object representing the user to create a profile for.
        """
        user = db.User.get_or_none(db.User.id == member.id)

        if not user:
            statistics = db.User.Statistic.create()
            daily_prog = db.User.DailyProgress.create()
            weekly_prog = db.User.WeeklyProgress.create()

            db.User.create(
                id=member.id,
                daily_progress=daily_prog,
                weekly_progress=weekly_prog,
                statistics=statistics
            )

        self.__get_tasks()

    def __clear_tasks(self, task_type: str):
        """
        Delete daily or weekly tasks and progress for all users.

        :param task_type: The type of tasks to delete. Can be 'daily' or 'weekly'.
        """
        users = list(db.User.select())

        for user in users:
            tasks = getattr(user, f"{task_type}_tasks")
            progress = getattr(user, f"{task_type}_progress")

            # Clear tasks and reset progress
            tasks.clear()
            progress.time_in_voice = 0
            progress.messages_send = 0
            progress.movies_guessed = 0

            # Delete all tasks
            for task in tasks:
                task.delete_instance()

            # Save changes to user and progress
            user.save()
            progress.save()

        # Refresh tasks
        self.__get_tasks()

    def __get_tasks(self):
        """
        Get daily and weekly tasks for all users.

        Generates new tasks for users who have no tasks.

        Assign tasks randomly from a list of possible tasks.

        If a task requires guessing movies, it checks how many movies the user has already guessed and chooses a new task if necessary.

        Save changes to the database.
        """
        # Get all users
        users = list(db.User.select())

        # Load possible tasks from JSON file
        with open('data/json/tasks.json', encoding='utf-8') as f:
            tasks = json.load(f)

        possible_tasks = {
            "daily": tasks["dailies"],
            "weekly": tasks["weeklies"]
        }

        # Load movie levels from JSON file
        with open('data/json/movies.json', encoding='utf-8') as f:
            levels = json.load(f)

        for user in users:
            for task_type in ['daily', 'weekly']:
                tasks = getattr(user, f"{task_type}_tasks")

                # Generate new tasks if user has none
                if len(tasks) == 0:
                    for x in range(0, 2):
                        task = random.choice(possible_tasks[task_type])

                        # Load movie levels from JSON file
                        with open('data/json/movies.json', encoding='utf-8') as f:
                            levels = json.load(f)

                        # Check how many movies the user has already guessed
                        guessed_movies = len(db.MovieGuess.select().where(db.MovieGuess.user == user).execute())

                        # If task requires guessing movies, choose a new task if user has already guessed enough movies
                        while task["accomplish_type"] == "movle_game":
                            if task["amount"] < (len(levels) - guessed_movies):
                                break

                            possible_tasks[task_type].remove(task)
                            task = random.choice(possible_tasks[task_type])

                        # Add new task to user's tasks
                        task_model = getattr(db.User, f"{task_type.title()}Task")
                        tasks.add(
                            task_model.create(
                                description=task["description"],
                                accomplish_type=task["accomplish_type"],
                                amount=task["amount"],
                                xp=task["xp"])
                        )
                        possible_tasks[task_type].remove(task)

            # Save changes to user
            user.save()
            return self

    def check_user_progress(self, member: nextcord.Member):
        """
        Checks the progress of a user's daily and weekly tasks and updates the user's XP accordingly.

        :param member: The member whose progress should be checked.

        :raise ValueError: If the user profile for the given member is not found.
        """
        user_profile = db.User.get_or_none(id=member.id)
        if user_profile is None:
            raise ValueError("User profile not found")

        # Combine daily and weekly tasks into one list
        tasks = user_profile.daily_tasks + user_profile.weekly_tasks
        # Create a dictionary to easily access the progress type for each task type
        progress_types = {
            "daily": user_profile.daily_progress,
            "weekly": user_profile.weekly_progress,
        }

        for task in tasks:
            # Get the progress type for this task
            progress = 0
            progress_type = progress_types[task.task_type]

            # Determine the progress based on the accomplishment type
            if task.accomplish_type == "minutes_in_voice":
                progress = progress_type.time_in_voice
            elif task.accomplish_type == "send_messages":
                progress = progress_type.messages_send
            elif task.accomplish_type == "movle_game":
                progress = progress_type.movies_guessed

            # If the task is completed, update the user's XP and mark the task as completed
            if task.amount <= progress and not task.completed:
                task.completed = True

                user_profile.xp += task.xp
                user_profile.save()
                task.save()

        return self

    async def __initiate_instances(self, sessions: list, views: dict) -> int:
        """
        Initializes the Discord voice connections for each session and reconnects if necessary.

        :param sessions: The list of sessions to initialize.
        :param views: The list of views to associate with each session.

        :return int: The number of sessions initialized.
        """
        # Disconnect from any existing voice clients
        for guild in self.__bot.guilds:
            bot_client = guild.voice_client
            if bot_client is not None:
                await bot_client.disconnect(force=True)

        # Reinitialize each session and view
        methods = [self.__reinit_session(session, views) for session in sessions]
        await asyncio.gather(*methods)

        # Return the number of sessions initialized
        return len(sessions)

    async def __reinit_session(self, session: db.Instance, views: dict):
        """
        Reinitializes the given session by creating a new command instance and initiating it. If an error occurs, deletes
        all poll votes and the instance from the database, and deletes the corresponding message if possible.

        :param session: Session to reinitialize.
        :param views: Dictionary containing callback functions for each session type.
        """
        try:
            command = instance.Instance(view_callback=views[session.type], bot_instance=self)
            await command.initiate(session)
        except Exception as e:
            print(f"Error in '__reinit_session' ({session.id}):\n{e}")
            db.PollVote.delete().where(db.PollVote.poll_id == session.id).execute()
            db.Instance.delete().where(db.Instance.id == session.id).execute()

            try:
                guild = self.__bot.get_guild(session.guild.id)
                channel = guild.get_channel(session.channel_id)
                message = await channel.fetch_message(session.id)

                await message.delete()
            except Exception as e:
                print(f"Error deleting message in '__reinit_session' ({session.id}):\n{e}")

    async def __reinit_voice_sessions(self, guild: nextcord.Guild) -> int:
        """
        Reinitializes voice sessions for a given guild.
        Deletes voice sessions for users who are no longer members of the guild.
        :param guild: The guild to reinitialize voice sessions for.
        :return: The number of reinitialized voice sessions.
        """
        voice_sessions = db.VoiceSession.select().where(db.VoiceSession.guild == guild.id)

        num_reinitialized_sessions = 0
        for voice_session in voice_sessions:
            member = guild.get_member(int(voice_session.user.id))
            if member:
                listener = on_voice_state_update_listener.Listener(self)
                listener.init_worker_thread(member, guild)
                num_reinitialized_sessions += 1
            else:
                voice_session.delete_instance()

        return num_reinitialized_sessions

    async def __run_scheduled_tasks(self):
        """
        Runs scheduled tasks at specified times.
        """
        # Clear daily and weekly tasks before scheduling them again
        schedule.clear('daily-tasks')
        schedule.clear('weekly-tasks')

        # Schedule daily and weekly tasks
        schedule.every().day.at("00:00").do(self.__clear_tasks, "daily").tag('daily-tasks', 'tasks')
        schedule.every().monday.at("00:00").do(self.__clear_tasks, "weekly").tag('weekly-tasks', 'tasks')

        while True:
            # Run scheduled tasks
            schedule.run_pending()
            # Wait for 1 second before checking again
            await asyncio.sleep(1)

    def __init_events(self):
        """
        Initialisiert alle Bot-Events.
        """
        bot = self.__bot

        @bot.event
        async def on_ready():
            """
            Event-Handler für das 'on_ready'-Event.
            """
            if not self.__is_already_running:
                await self.__bot.sync_all_application_commands()

                guilds = list(db.Guild.select())
                guild_ids = []
                now = datetime.now()

                for guild in guilds:
                    guild_ids.append(guild.id)

                print("(BOT) " + bot.user.name + " ist bereit [{}]".format(now.strftime("%d/%m/%Y, %H:%M:%S")))
                print("(BOT) Vorhandene Guilden ({}):".format(len(bot.guilds)))

                for guild in bot.guilds:
                    print("\t- " + guild.name + "\t" + Fore.CYAN + str(guild.id) + Style.RESET_ALL)

                asyncio.create_task(self.__run_scheduled_tasks())

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
            """
            Event-Handler für das 'on_message'-Event.
            """
            if type(message.author) is nextcord.Member:
                self.create_user_profile(message.author)

            listener = on_message_listener.Listener(self)
            await listener.call(message)

        @bot.event
        async def on_raw_message_delete(payload: nextcord.RawMessageDeleteEvent):
            """
            Event-Handler für das 'on_raw_message_delete'-Event.
            """
            listener = on_raw_message_delete_listener.Listener(self)
            await listener.call(payload)

        @bot.event
        async def on_member_join(member: nextcord.Member):
            """
            Event-Handler für das 'on_member_join'-Event.
            """
            self.create_user_profile(member)

            listener = on_member_join_listener.Listener(self)
            await listener.call(member)

        @bot.event
        async def on_member_remove(member: nextcord.Member):
            """
            Event-Handler für das 'on_member_remove'-Event.
            """
            listener = on_member_remove_listener.Listener(self)
            await listener.call(member)

        @bot.event
        async def on_voice_state_update(
                member: nextcord.Member,
                before: nextcord.VoiceState,
                after: nextcord.VoiceState
        ):
            """
            Event-Handler für das 'on_voice_state_update'-Event.
            """
            self.create_user_profile(member)

            listener = on_voice_state_update_listener.Listener(self)
            await listener.call(member, before, after)

        @bot.event
        async def on_guild_available(guild: nextcord.Guild):
            """
            Event-Handler für das 'on_guild_available'-Event.
            Erstellt automatisch Einstellungen für den Server, wenn dieser zum ersten Mal verfügbar ist.
            """
            guilds = list(db.Guild.select())
            guild_ids = []

            for guild_ in guilds:
                guild_ids.append(guild_.id)

            for guild_ in bot.guilds:
                if guild_.id not in guild_ids:
                    settings = db.Guild.Setting.create()
                    db.Guild.create(id=guild_.id, settings=settings)

            sessions = list(db.Instance.select().where(db.Instance.guild == guild.id))

            views = {
                "order66": order66_view.View,
                "calculator": calculator_view.View,
                "poll": poll_view.View,
                "backup": backup_view.View,
                "tts": tts_view.View,
                "profile": profile_view.View,
                "movie": movie_view.View,
                "status": play_view.View,
                "search": search_view.View,
                "config": config_view.View,
                "queue": queue_view.View,
                "user": user_view.View
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
            """
            Event-Handler für das 'on_guild_join'-Event.
            Erstellt automatisch Einstellungen für den Server, wenn dieser zum ersten Mal beigetreten wird.
            """
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
            """
            Event-Handler für das 'on_guild_remove'-Event.
            """
            listener = on_guild_remove_listener.Listener(self)
            await listener.call(guild)

    def __init_commands(self):
        bot = self.__bot

        @bot.slash_command(
            description="Opens an individual calculator, that supports basic mathematical equations."
        )
        async def calculator(
                interaction: nextcord.Interaction
        ):
            """
            Opens an individual calculator, that supports basic mathematical equations.
            """
            command = instance.Instance(view_callback=calculator_view.View, bot_instance=self)
            await command.create(interaction, "calculator")

        @bot.slash_command(
            description="Creates a poll with one question and an amount of answers from 1 - 4."
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
            """
            Creates a poll with one question and an amount of answers from 1 - 4.
            """
            await interaction.response.send_modal(poll_view.Modal(number, self, interaction.guild))

        @bot.slash_command(
            description="That's how the weather outside is, for you caveman!"
        )
        async def weather(
                interaction: nextcord.Interaction,
                city: str = nextcord.SlashOption(
                    name="city",
                    description="Where should I look?"
                )
        ):
            """
            That's how the weather outside is, for you caveman!
            """
            command = weather_command.Command(interaction, self, {"city": city})
            await command.run()

        @bot.slash_command(
            description="Shows a random image and fact!"
        )
        async def animal(
                interaction: nextcord.Interaction,
                target: str = nextcord.SlashOption(
                    name="animal",
                    description="What animal do you want to see?",
                    choices=["bird", "cat", "dog", "fox", "kangaroo", "koala", "panda", "raccoon", "red_panda"],
                    default="raccoon",
                    required=True
                )
        ):
            """
            Shows a random image and fact!
            """
            command = animal_command.Command(interaction, self, {"animal": target})
            await command.run()

        @bot.slash_command(
            description="Deletes an amount of messages"
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
            """
            Deletes an amount of messages
            """
            command = purge_command.Command(interaction, self, {"amount": amount})
            await command.run()

        @bot.slash_command(
            description="Shows a random meme from a subreddit!"
        )
        async def meme(
                interaction: nextcord.Interaction,
                subreddit: str = nextcord.SlashOption(
                    name="subreddit",
                    description="Subreddit the meme should be from!",
                    required=False
                )
        ):
            """
            Shows a random meme from a subreddit!
            """
            command = meme_command.Command(interaction, self, {"subreddit": subreddit})
            await command.run()

        @bot.slash_command()
        async def faq(
                interaction: nextcord.Interaction
        ):
            """
            Command-container for subcommands
            """
            pass

        @faq.subcommand(
            description="Uptime of E.D.I.T.H!"
        )
        async def up(
                interaction: nextcord.Interaction
        ):
            """
            Shows the uptime of E.D.I.T.H.
            """
            command = up_command.Command(interaction, self)
            await command.run()

        @faq.subcommand(
            description="About E.D.I.T.H!"
        )
        async def about(
                interaction: nextcord.Interaction
        ):
            """
            Shows information about E.D.I.T.H.
            """
            command = about_command.Command(interaction, self)
            await command.run()

        @bot.slash_command(
            description="Executes the order-66!"
        )
        @check(lambda i: i.user.id == 243747656470495233)
        async def order66(
                interaction: nextcord.Interaction,
                target: nextcord.User = nextcord.SlashOption(
                    name="target",
                    description="Who is you target?",
                    required=True
                )
        ):
            """
            Executes the order-66!
            """
            command = instance.Instance(view_callback=order66_view.View, bot_instance=self)
            await command.create(interaction, "order66", data={"target": target.id})

        @bot.slash_command(
            description="Plays a custom phrase!"
        )
        async def tts(
                interaction: nextcord.Interaction,
                phrase: str = nextcord.SlashOption(
                    name="phrase",
                    description="What should I say?"
                )
        ):
            """
            Plays a custom phrase!
            """
            command = instance.Instance(view_callback=tts_view.View, bot_instance=self)
            await command.create(interaction, "tts", data={"phrase": phrase})

        @bot.slash_command(
            description="Shows your or someone elses profile!"
        )
        async def profile(
                interaction: nextcord.Interaction,
                user: nextcord.User = nextcord.SlashOption(
                    name="user",
                    description="From who do you want to see the profile?",
                    required=False
                )
        ):
            """
            Shows your or someone else's profile!
            :param interaction: The interaction object representing the user's interaction with the bot.
            :param user: The optional user whose profile is being viewed.
            """
            # If no user is specified, show the profile of the interaction's user.
            profile_user = user or interaction.user

            # Create a command to display the profile view.
            profile_view_command = instance.Instance(view_callback=profile_view.View, bot_instance=self)

            # Create and send the profile view.
            await profile_view_command.create(
                interaction,
                "profile",
                data={"user": profile_user.id}
            )

        @bot.slash_command(
            description="Opens the backup-terminal!",
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
        @backup.error
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
