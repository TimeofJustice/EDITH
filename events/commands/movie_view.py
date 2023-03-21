import json
import random
from difflib import SequenceMatcher

import nextcord

import db
from events import view
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__clue = 0
        self.__color = nextcord.Colour.random()
        self.__level = None
        self.__level_key = None
        self.__active_clue = 0

        self.__start_level = Button(label="Start", row=0, args=("start",),
                                    style=nextcord.ButtonStyle.green, callback=self.__callback_start)
        self.__close = Button(label="Close", row=0, args=("close",),
                              style=nextcord.ButtonStyle.red, callback=self.__callback_close)
        self.__next_level = Button(label="Next", row=0, args=("next",),
                                   style=nextcord.ButtonStyle.blurple, callback=self.__callback_next)

        self.__clue_one = Button(label="Clue 1", row=0, args=("one",),
                                 style=nextcord.ButtonStyle.grey, callback=self.__callback_clue_one)
        self.__clue_two = Button(label="Clue 2", row=0, args=("two",),
                                 style=nextcord.ButtonStyle.grey, callback=self.__callback_clue_two)
        self.__clue_three = Button(label="Clue 3", row=0, args=("three",),
                                   style=nextcord.ButtonStyle.grey, callback=self.__callback_clue_three)

        self.__clue_reveal = Button(label="Reveal Clue", row=0, args=("reveal",),
                                    style=nextcord.ButtonStyle.blurple, callback=self.__callback_reveal)

        self.__clue_guess = Button(label="Guess", row=0, args=("guess",),
                                   style=nextcord.ButtonStyle.green, callback=self.__callback_guess)

        self.__forfeit = Button(label="Forfeit", row=0, args=("forfeit",),
                                style=nextcord.ButtonStyle.red, callback=self.__callback_forfeit)

    async def init(self, **kwargs):
        self.clear_items()
        self.add_item(self.__start_level)
        self.add_item(self.__close)

        with open('data/json/movies.json', encoding='utf-8') as f:
            levels = json.load(f)

        guessed_movies = len(self.__mysql.select(table="movie_guessing", colms="movie_id",
                                                 clause=f"WHERE user_id={self.__author.id}"))
        guessed_movies_one = len(self.__mysql.select(table="movie_guessing", colms="movie_id",
                                                     clause=f"WHERE user_id={self.__author.id} and clues=1"))
        guessed_movies_two = len(self.__mysql.select(table="movie_guessing", colms="movie_id",
                                                     clause=f"WHERE user_id={self.__author.id} and clues=2"))
        guessed_movies_three = len(self.__mysql.select(table="movie_guessing", colms="movie_id",
                                                       clause=f"WHERE user_id={self.__author.id} and clues=3"))

        if guessed_movies == len(levels):
            self.remove_item(self.__start_level)

        embed = nextcord.Embed(
            title="Introduction",
            description=f"You will receive three clues and your goal is to guess the right movie.\n"
                        f"There are currently **{len(levels)}** levels.",
            colour=self.__color
        )

        embed.add_field(
            name="Experience",
            value="You can gain xp for guessing the right movie.\n"
                  "The fewer clues you need, the more xp you can gain:\n\n"
                  "Clue 1: **500xp**\n"
                  "Clue 2: **300xp**\n"
                  "Clue 3: **100xp**"
        )

        embed.add_field(
            name="\u200b",
            value="\u200b"
        )

        embed.add_field(
            name="Stats",
            value=f"Guessed movies: **{guessed_movies}/{len(levels)}**\n\n"
                  f"Movie guessed with:\n"
                  f"One clue: **{guessed_movies_one}**\n"
                  f"Two clues: **{guessed_movies_two}**\n"
                  f"Three clues: **{guessed_movies_three}**\n"
        )

        embed.add_field(
            name="Instructions",
            value=f"You have the opportunity to either guess the movie or reveal the next clue.\n"
                  f"**Guessing**\n"
                  f"While guessing you have to enter the movie titel. "
                  f"After entering a title you will receive an hint how close you are.\n\n"
                  f"There are three levels:\n"
                  f"**Not even close** means your title is **less** then **60%** accurate.\n"
                  f"**You are close** means your title is **less** then **90%** accurate.\n"
                  f"**You guessed it** means your title is **more** than **90%** accurate.\n\n"
                  f"You can enter the **english** or the **german** title. "
                  f"You have two possible titles the short-title and the full-title.\n"
                  f"For example:\n"
                  f"- Pirates of the Caribbean\n"
                  f"- Pirates of the Caribbean: The Curse of the Black Pearl\n"
                  f"**You can decide** which title-form you want to guess.\n\n"
                  f"**Reveal clue**\n"
                  f"After revealing the next clue you can always switch between the revealed clues.\n"
                  f"Keep in mind, that you gain **less** xp with more revealed clues."
        )

        embed.set_author(name="Movle (A movie guessing game)")
        embed.set_footer(text="ㅤ" * 40)

        await self.__message.edit(content="", embed=embed, view=self, attachments=[])

    async def __callback_start(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            self.__clue = 1
            guessed_movies = self.__mysql.select(table="movie_guessing", colms="movie_id",
                                                 clause=f"WHERE user_id={self.__author.id}")

            with open('data/json/movies.json', encoding='utf-8') as f:
                levels = json.load(f)

            if len(guessed_movies) == len(levels):
                await self.init()
            else:
                for movie in guessed_movies:
                    levels.pop(movie["movie_id"])

                rand_key = random.choice(list(levels.keys()))

                self.__level = levels[rand_key]
                self.__level_key = rand_key

                await self.__callback_clue_one(interaction, args)

        return args

    async def __callback_close(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            await self.__message.delete()
            db.Instance.delete().where(db.Instance.id == self.__message.id).execute()

        return args

    async def __callback_next(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            await self.__callback_start(interaction, args)

        return args

    async def __callback_clue_one(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            self.__active_clue = 1

            self.clear_items()
            self.__set_clue_buttons()
            self.add_item(self.__clue_guess)
            self.add_item(self.__forfeit)

            self.__clue_one.disabled = True
            self.__clue_one.style = nextcord.ButtonStyle.blurple

            if args[0] == "guessed":
                title = f"Clue 1 ({args[1]})"
            else:
                title = f"Clue 1"

            embed = nextcord.Embed(
                title=title,
                description=self.__level["clue_one"]["description"],
                colour=self.__color
            )

            embed.set_author(name="Movle (A movie guessing game)")
            embed.set_footer(text=f"(ID: {self.__level['id']})" + "ㅤ" * 26)

            if self.__level["clue_one"]["type"] == "image":
                embed.set_image(url="attachment://cover.png")

                with open(self.__level["clue_one"]["file_path"], 'rb') as fp:
                    file = nextcord.File(fp, 'cover.png')

                await self.__message.edit(content="", embed=embed, view=self, file=file)
            elif self.__level["clue_one"]["type"] == "audio":
                with open(self.__level["clue_one"]["file_path"], 'rb') as fp:
                    file = nextcord.File(fp, 'audio.mp3')

                await self.__message.edit(content="", embed=embed, view=self, file=file)
            else:
                await self.__message.edit(content="", embed=embed, view=self, attachments=[])

        return args

    async def __callback_clue_two(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            self.__active_clue = 2

            self.clear_items()
            self.__set_clue_buttons()
            self.add_item(self.__clue_guess)
            self.add_item(self.__forfeit)

            self.__clue_two.disabled = True
            self.__clue_two.style = nextcord.ButtonStyle.blurple

            if args[0] == "guessed":
                title = f"Clue 2 ({args[1]})"
            else:
                title = f"Clue 2"

            embed = nextcord.Embed(
                title=title,
                description=self.__level["clue_two"]["description"],
                colour=self.__color
            )

            embed.set_author(name="Movle (A movie guessing game)")
            embed.set_footer(text=f"(ID: {self.__level['id']})" + "ㅤ" * 26)

            if self.__level["clue_two"]["type"] == "image":
                embed.set_image(url="attachment://cover.png")

                with open(self.__level["clue_two"]["file_path"], 'rb') as fp:
                    file = nextcord.File(fp, 'cover.png')

                await self.__message.edit(content="", embed=embed, view=self, file=file)
            elif self.__level["clue_two"]["type"] == "audio":
                with open(self.__level["clue_two"]["file_path"], 'rb') as fp:
                    file = nextcord.File(fp, 'audio.mp3')

                await self.__message.edit(content="", embed=embed, view=self, file=file)
            else:
                await self.__message.edit(content="", embed=embed, view=self, attachments=[])

        return args

    async def __callback_clue_three(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            self.__active_clue = 3

            self.clear_items()
            self.__set_clue_buttons()
            self.add_item(self.__clue_guess)
            self.add_item(self.__forfeit)

            self.__clue_three.disabled = True
            self.__clue_three.style = nextcord.ButtonStyle.blurple

            if args[0] == "guessed":
                title = f"Clue 3 ({args[1]})"
            else:
                title = f"Clue 3"

            embed = nextcord.Embed(
                title=title,
                description=self.__level["clue_three"]["description"],
                colour=self.__color
            )

            embed.set_author(name="Movle (A movie guessing game)")
            embed.set_footer(text=f"(ID: {self.__level['id']})" + "ㅤ" * 26)

            if self.__level["clue_three"]["type"] == "image":
                embed.set_image(url="attachment://cover.png")

                with open(self.__level["clue_three"]["file_path"], 'rb') as fp:
                    file = nextcord.File(fp, 'cover.png')

                await self.__message.edit(content="", embed=embed, view=self, file=file)
            elif self.__level["clue_three"]["type"] == "audio":
                with open(self.__level["clue_three"]["file_path"], 'rb') as fp:
                    file = nextcord.File(fp, 'audio.mp3')

                await self.__message.edit(content="", embed=embed, view=self, file=file)
            else:
                await self.__message.edit(content="", embed=embed, view=self, attachments=[])

        return args

    def __set_clue_buttons(self):
        self.add_item(self.__clue_one)

        if 1 < self.__clue:
            self.add_item(self.__clue_two)

        if 2 < self.__clue:
            self.add_item(self.__clue_three)

        if self.__clue != 3:
            self.add_item(self.__clue_reveal)

        self.__clue_one.disabled = False
        self.__clue_one.style = nextcord.ButtonStyle.grey
        self.__clue_two.disabled = False
        self.__clue_two.style = nextcord.ButtonStyle.grey
        self.__clue_three.disabled = False
        self.__clue_three.style = nextcord.ButtonStyle.grey

    async def __callback_reveal(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            if self.__clue == 1:
                self.__clue += 1
                await self.__callback_clue_two(interaction, args)
            elif self.__clue == 2:
                self.__clue += 1
                await self.__callback_clue_three(interaction, args)

        return args

    async def __callback_guess(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=False):
            await interaction.response.send_modal(Modal(self, interaction))

        return args

    @staticmethod
    def similar(a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    async def send_guess(self, title, interaction: nextcord.Interaction):
        percs = []

        for short_title in self.__level["title_short"]:
            percs.append(self.similar(title, short_title))

        for full_title in self.__level["title_full"]:
            percs.append(self.similar(title, full_title))

        perc = max(percs)

        if perc < 0.9:
            if perc < 0.6:
                status = "Not even close"
            else:
                status = "You are close"

            if self.__active_clue == 1:
                await self.__callback_clue_one(interaction, ("guessed", status))
            elif self.__active_clue == 2:
                await self.__callback_clue_two(interaction, ("guessed", status))
            else:
                await self.__callback_clue_three(interaction, ("guessed", status))
        else:
            await self.__guessed()

    async def __guessed(self):
        self.clear_items()
        self.add_item(self.__next_level)
        self.add_item(self.__close)

        self.__mysql.insert(table="movie_guessing", colms="(user_id, movie_id, clues)",
                            values=(self.__author.id, self.__level_key, self.__clue))

        if self.__clue == 1:
            self.__mysql.update(table="user_profiles", value="xp=xp+500",
                                clause=f"WHERE id={self.__author.id}")
        elif self.__clue == 2:
            self.__mysql.update(table="user_profiles", value="xp=xp+300",
                                clause=f"WHERE id={self.__author.id}")
        elif self.__clue == 3:
            self.__mysql.update(table="user_profiles", value="xp=xp+100",
                                clause=f"WHERE id={self.__author.id}")

        self.__mysql.update(table="user_profiles", value="movle_daily=movle_daily+1",
                            clause=f"WHERE id={self.__author.id}")
        self.__mysql.update(table="user_profiles", value="movle_weekly=movle_weekly+1",
                            clause=f"WHERE id={self.__author.id}")

        self.__bot_instance.check_user_progress(self.__author)

        embed = nextcord.Embed(
            title="You guessed it!",
            description=f"The movie was indeed **{self.__level['title_full'][0]}**\n",
            colour=self.__color
        )

        embed.set_image(url="attachment://cover.png")

        with open(self.__level['cover'], 'rb') as fp:
            file = nextcord.File(fp, 'cover.png')

        embed.set_author(name="Movle (A movie guessing game)")
        embed.set_footer(text=f"(ID: {self.__level['id']})" + "ㅤ" * 20)

        await self.__message.edit(content="", embed=embed, view=self, file=file)

    async def __callback_forfeit(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            await self.init()

        return args


class Modal(nextcord.ui.Modal):
    def __init__(self, command_instance, interaction):
        self.__command_instance = command_instance
        self.__interaction = interaction
        super().__init__("Movle (A movie guessing game)")

        self.__title = nextcord.ui.TextInput(label=f"Whats your guess?", style=nextcord.TextInputStyle.short,
                                             placeholder=f"Title?", required=True)
        self.add_item(self.__title)

        pass

    async def callback(self, interaction: nextcord.Interaction):
        await self.__command_instance.send_guess(self.__title.value, self.__interaction)
