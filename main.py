import _thread
import asyncio
import configparser
from datetime import datetime
import os
from pathlib import Path
import nextcord
from nextcord.ext import commands
from colorama import Style, Fore
from nextcord.ext.application_checks import has_permissions, ApplicationMissingPermissions

import instance
from events.commands import calculator, poll as poll_, \
    weather as weather_, purge as purge_, meme as meme_
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
            "calculator": calculator.View,
            "poll": poll_.View
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
            guild = message.guild
            channel = message.channel
            author = message.author

            if guild is not None:
                guild_settings = \
                    mysql.select(table="guilds",
                                 colms="guilds.id, settings.messages_channel, settings.id AS settings_id",
                                 clause=f"INNER JOIN settings ON guilds.settings=settings.id WHERE guilds.id={guild.id}")[
                        0]

                if guild_settings["messages_channel"] is not None and not author.bot:
                    messages_channel = guild.get_channel(guild_settings["messages_channel"])

                    embed = nextcord.Embed(
                        color=nextcord.Colour.green(),
                        description=message.content
                    )

                    embed.set_author(name=f"Message send (ID:{message.id})")
                    embed.add_field(name="Author", value=f"**Discord-Name:** {author.name} (ID:{author.id})\n"
                                                         f"**Server-Name:** {author.display_name}")

                    embed.add_field(name="Channel",
                                    value=f"**Category:** {channel.category}\n"
                                          f"**Channel:** {channel} (ID:{channel.id})")

                    if message.attachments:
                        for attachment in message.attachments:
                            attachments = f"Name: {attachment.filename}\n" \
                                          f"URL: {attachment.url}\n\n"

                            embed.add_field(name="Attachment", value=attachments, inline=False)
                            embed.set_image(url=attachment.url)

                    await messages_channel.send(embed=embed)

                if not author.bot:
                    print("User gained Point")

        @bot.event
        async def on_raw_message_delete(payload: nextcord.RawMessageDeleteEvent):
            guild = bot.get_guild(payload.guild_id)

            if guild is not None:
                channel = guild.get_channel(payload.channel_id)

                guild_settings = mysql.select(table="guilds",
                                              colms="guilds.id, settings.messages_channel, settings.id AS settings_id",
                                              clause=f"INNER JOIN settings ON guilds.settings=settings.id "
                                                     f"WHERE guilds.id={guild.id}")[0]

                if guild_settings["messages_channel"] is not None and channel.id != guild_settings["messages_channel"]:
                    messages_channel = guild.get_channel(guild_settings["messages_channel"])

                    embed = nextcord.Embed(
                        color=nextcord.Colour.red()
                    )

                    embed.set_author(name=f"Message deleted (ID:{payload.message_id})")

                    embed.add_field(name="Channel",
                                    value=f"**Category:** {channel.category}\n"
                                          f"**Channel:** {channel} (ID:{channel.id})")

                    await messages_channel.send(embed=embed)

        '''
        on_raw_message_edit
        on_raw_reaction_add
        on_raw_reaction_remove
        on_raw_reaction_clear
        on_raw_reaction_clear_emoji
        on_guild_channel_delete
        on_guild_channel_create
        on_guild_channel_update
        on_guild_channel_pins_update
        on_thread_join
        on_thread_remove
        on_thread_delete
        on_thread_member_join
        on_thread_member_remove
        on_thread_update
        on_guild_integrations_update
        on_integration_create
        on_integration_update
        on_raw_integration_delete
        on_webhooks_update
        on_member_join
        on_member_remove
        on_member_update
        on_user_update
        on_guild_update
        on_guild_role_create
        on_guild_role_delete
        on_guild_role_update
        on_guild_emojis_update
        on_guild_stickers_update
        on_voice_state_update
        on_stage_instance_create
        on_stage_instance_delete
        on_stage_instance_update
        on_member_ban
        on_member_unban
        on_invite_create
        on_invite_delete
        on_guild_scheduled_event_create
        on_guild_scheduled_event_update
        on_guild_scheduled_event_delete
        on_guild_scheduled_event_user_add
        on_guild_scheduled_event_user_remove
        on_auto_moderation_rule_create
        on_auto_moderation_rule_update
        on_auto_moderation_rule_delete
        on_auto_moderation_action_execution
        
        Low:
        - 
        Middle:
        - 
        High:
        - 
        Highest:
        - 
        '''

        '''
        on_member_join
        on_member_remove
        on_guild_join
        on_guild_remove
        on_message (Points)
        scm
        '''

    def __init_commands(self):
        bot = self.__bot
        mysql = self.__mysql

        guilds_data = mysql.select(table="guilds", colms="id")
        guild_ids = []

        for guild_data in guilds_data:
            guild_ids.append(guild_data["id"])

        @bot.slash_command(
            description="Opens an individual calculator, that supports basic mathematical equations.",
            guild_ids=guild_ids
        )
        async def calc(
                interaction: nextcord.Interaction
        ):
            command = instance.Instance(view_callback=calculator.View, bot_instance=self)
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
            await interaction.response.send_modal(poll_.Modal(number, self, interaction.guild))

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
            command = weather_.Command(interaction, self, {"city": city})
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
            command = purge_.Command(interaction, self, {"amount": amount})
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
            command = meme_.Command(interaction, self, {"subreddit": subreddit})
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
            text = f"Online since {self.get_running_time()}!"
            msg = nextcord.Embed(
                title="",
                description=text,
                color=nextcord.Colour.gold()
            )

            await interaction.send(embed=msg, ephemeral=True)

        @faq.subcommand(
            description="About E.D.I.T.H!"
        )
        async def about(
                interaction: nextcord.Interaction
        ):
            owner = await bot.fetch_user(243747656470495233)

            embed = nextcord.Embed(
                title="About E.D.I.T.H!",
                description=f"I am **E.D.I.T.H**, I am the 4. generation of the bot from {owner.mention}.\n"
                            f"\n"
                            f"Developed in **Python** via **nextcord**.\n"
                            f"I am the version **{self.get_version()}**!",
                colour=nextcord.Colour.random()
            )

            await interaction.send(embed=embed, ephemeral=True)

        @bot.slash_command(
            description="Activates the E.D.I.T.H. logging-tool!",
            guild_ids=guild_ids
        )
        @has_permissions(administrator=True)
        async def logging(
                interaction: nextcord.Interaction,
                status: int = nextcord.SlashOption(
                    name="level",
                    description="What level of logging do you want to use?",
                    choices={"off": 0, "low": 1, "middle": 2, "high": 3, "highest": 4}
                )
        ):
            guild = interaction.guild

            guild_settings = mysql.select(table="guilds",
                                          colms="guilds.id, settings.log_category, settings.id AS settings_id",
                                          clause=f"INNER JOIN settings ON guilds.settings=settings.id "
                                                 f"WHERE guilds.id={guild.id}")[0]

            if status != 0 and guild_settings["log_category"] is None:
                category = await guild.create_category(name="E.D.I.T.H Logging")
                messages_channel = await category.create_text_channel(name="messages")

                await category.set_permissions(guild.default_role, view_channel=False)

                mysql.update(table="settings", value=f"log_category={category.id}",
                             clause=f"WHERE id='{guild_settings['settings_id']}'")
                mysql.update(table="settings", value=f"messages_channel={messages_channel.id}",
                             clause=f"WHERE id='{guild_settings['settings_id']}'")

                embed = nextcord.Embed(
                    description="The logging-tool is now enabled!",
                    colour=nextcord.Colour.green()
                )
            elif status != 0 and guild_settings["log_category"] is not None:
                embed = nextcord.Embed(
                    description="The logging-tool is already running!",
                    colour=nextcord.Colour.red()
                )
            else:
                category = guild.get_channel(guild_settings["log_category"])
                channels = category.channels

                for channel in channels:
                    await channel.delete()

                await category.delete()

                mysql.update(table="settings", value=f"log_category=Null",
                             clause=f"WHERE id='{guild_settings['settings_id']}'")
                mysql.update(table="settings", value=f"messages_channel=Null",
                             clause=f"WHERE id='{guild_settings['settings_id']}'")

                embed = nextcord.Embed(
                    description="The logging-toll is now disabled!",
                    colour=nextcord.Colour.orange()
                )

            await interaction.send(embed=embed, ephemeral=True)

        @purge.error
        @logging.error
        async def command_error(error: nextcord.Interaction, ctx):
            if type(ctx) == ApplicationMissingPermissions:
                embed = nextcord.Embed(
                    color=nextcord.Colour.orange(),
                    description="**YOU SHALL NOT PASS**"
                )

                embed.set_image(url="attachment://403.png")

                with open('pics/403.png', 'rb') as fp:
                    await error.send(embed=embed, ephemeral=True, file=nextcord.File(fp, '403.png'))

        '''
        achievements
        r6s
        logs
        order66
        random
        music (search, play, stop, pause, resume, skip, status, queue)
        backup
        tts
        settings (role, notifications, settings)
        scm
        profile (XP)
        playlists
        '''


client = Bot()
