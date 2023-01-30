import _thread
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
from events.commands import calculator as calculator_command, poll as poll_command, \
    weather as weather_command, purge as purge_command, meme as meme_command, up as up_command, about as about_command, \
    logging as logging_command, order66 as order66_command
from events.listeners import message as message_listener, message_delete as message_delete_listener
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

        self.__initiate_tables()
        self.__init_events()
        self.__init_commands()

        self.__bot.run(self.__token)

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

        mysql.create_table(table="guilds", colms="(id BIGINT(255) PRIMARY KEY,"
                                                 "settings VARCHAR(255),"
                                                 "FOREIGN KEY (settings) REFERENCES settings(id))")

        mysql.create_table(table="instances", colms="(message_id BIGINT(255) PRIMARY KEY,"
                                                    "author_id BIGINT(255) NOT NULL,"
                                                    "channel_id BIGINT(255) NOT NULL,"
                                                    "guild_id BIGINT(255) NOT NULL,"
                                                    "type VARCHAR(255) NOT NULL,"
                                                    "data VARCHAR(255))")

        mysql.create_table(table="poll_submits", colms="(id VARCHAR(255) primary key,"
                                                       "user_id BIGINT(255) not null,"
                                                       "poll_id BIGINT(255) not null,"
                                                       "FOREIGN KEY (poll_id) REFERENCES instances(message_id))")
        mysql.add_colm(table="poll_submits", colm="answer_id", definition="BIGINT(255)", clause="AFTER poll_id")

        mysql.create_table(table="custom_channels", colms="(id bigint(255) primary key,"
                                                          "guild_id bigint(255) not null)")

    async def __idle_handler(self):
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

    def __init_threads(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self.__idle_handler())
        loop.close()

    async def __initiate_instances(self):
        mysql = Mysql()
        sessions = mysql.select(table="instances", colms="*")
        views = {
            "calculator": calculator_command.View,
            "poll": poll_command.View,
            "order66": order66_command.View
        }

        start = datetime.now()
        for session in sessions:
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
        print(f"{Fore.GREEN}Es wurden {len(sessions)} Instanzen in "
              f"{(datetime.now() - start).seconds}s geladen.{Style.RESET_ALL}")

    def __init_events(self):
        bot = self.__bot
        mysql = self.__mysql

        @bot.event
        async def on_ready():
            if not self.__is_already_running:
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

                _thread.start_new_thread(self.__init_threads, ())
                await self.__initiate_instances()
            else:
                print("(BOT) Reconnected")

        @bot.event
        async def on_message(message: nextcord.Message):
            listener = message_listener.Listener(self)
            await listener.call(message)

        @bot.event
        async def on_raw_message_delete(payload: nextcord.RawMessageDeleteEvent):
            listener = message_delete_listener.Listener(self)
            await listener.call(payload)

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
            command = instance.Instance(view_callback=calculator_command.View, bot_instance=self)
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
            await interaction.response.send_modal(poll_command.Modal(number, self, interaction.guild))

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
            description="Activates the E.D.I.T.H. logging-tool!",
            guild_ids=guild_ids
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
            command = instance.Instance(view_callback=order66_command.View, bot_instance=self)
            await command.create(interaction, "order66", data={"target": target.id})

        @purge.error
        @logging.error
        @order66.error
        async def command_error(error: nextcord.Interaction, ctx):
            if type(ctx) == ApplicationMissingPermissions or type(ctx) == ApplicationCheckFailure:
                embed = nextcord.Embed(
                    color=nextcord.Colour.orange(),
                    title="**YOU SHALL NOT PASS**",
                    description="You don't have enough permission to perform this command!"
                )

                embed.set_image(url="attachment://403.png")

                with open('pics/403.png', 'rb') as fp:
                    await error.send(embed=embed, ephemeral=True, file=nextcord.File(fp, '403.png'))
            else:
                embed = nextcord.Embed(
                    color=nextcord.Colour.orange(),
                    title="**Unknown error**",
                    description=f"An **unknown error** occurred\n"
                                f"||{type(ctx)}||"
                )

                embed.set_image(url="attachment://unknown_error.gif")

                with open('pics/unknown_error.gif', 'rb') as fp:
                    await error.send(embed=embed, ephemeral=True, file=nextcord.File(fp, 'unknown_error.gif'))


client = Bot()
