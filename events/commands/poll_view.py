import json
from datetime import datetime
import nextcord

import db
from events import view, instance
from events.view import Button


class Modal(nextcord.ui.Modal):
    def __init__(self, questions, bot_instance, guild):
        self.__guild = guild
        self.__bot_instance = bot_instance
        super().__init__(f"Poll")

        self.__question = nextcord.ui.TextInput(label=f"Whats your question?", style=nextcord.TextInputStyle.short,
                                                placeholder=f"Question?", required=True)
        self.add_item(self.__question)
        self.__possibilities = []

        for i in range(0, questions):
            possibility = nextcord.ui.TextInput(label=f"{i + 1}. Answer",
                                                style=nextcord.TextInputStyle.short,
                                                placeholder=f"Answer",
                                                required=True)

            self.__possibilities.append([possibility])

            self.add_item(possibility)

    async def callback(self, interaction: nextcord.Interaction):
        title = self.__question.value

        if title[-1] != "?":
            title += "?"

        possibilities = []

        for possibility in self.__possibilities:
            possibilities.append([possibility[0].label, possibility[0].value])

        data = {"possibilities": possibilities, "question": title}

        command = instance.Instance(view_callback=View, bot_instance=self.__bot_instance)
        await command.create(interaction, "poll", data)


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__possibilities = instance_data["possibilities"]
        self.__question = instance_data["question"]

        self.__close = Button(label="Close", emoji="❌",
                              row=1, args=(),
                              style=nextcord.ButtonStyle.danger, callback=self.__callback_close)

        self.__dropdown = None

    def __is_author(self, interaction: nextcord.Interaction, exception_owner=False):
        user = interaction.user
        if self.__author.id == user.id or (exception_owner and user.id == self.__bot_instance.owner_id):
            return True
        else:
            return False

    async def init(self, **kwargs):
        self.__dropdown = PollDropdown(self.__possibilities, self.__question,
                                       self.__message, self.__author, self.__bot_instance)

        self.clear_items()
        self.add_item(self.__dropdown)
        self.add_item(self.__close)

        text = ""

        index = 0
        for possibility in self.__possibilities:
            submits = list(db.PollVote.select().where(
                db.PollVote.poll_id == self.__message.id,
                db.PollVote.answer_id == index
            ))

            text += f"{possibility[0]}: {possibility[1]} **({len(submits)})**\n"
            index += 1

        embed = nextcord.Embed(title=self.__question, description=text, timestamp=datetime.now(),
                               color=nextcord.Colour.blue())
        embed.set_author(name=self.__author.name, icon_url=self.__author.avatar)
        embed.set_footer(text="ㅤ" * 22)
        await self.__message.edit(content="", embed=embed, view=self)

    async def __callback_close(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, True):
            await self.__message.delete()

            db.PollVote.delete().where(
                db.PollVote.poll_id == self.__message.id
            ).execute()
            db.Instance.delete().where(
                db.Instance.id == self.__message.id
            ).execute()

            await interaction.response.send_message("Poll has been deleted.", ephemeral=True)
        else:
            await interaction.response.send_message("You are not the author of this poll.", ephemeral=True)


class PollDropdown(nextcord.ui.Select):
    def __init__(self, possibilities, question, message, author, bot_instance):
        options = []
        self.__message = message
        self.__guild = message.guild
        self.__question = question
        self.__possibilities = possibilities
        self.__author = author
        self.__bot_instance = bot_instance
        if type(possibilities) is str:
            self.__possibilities = json.loads(self.__possibilities)

        for answer in range(0, len(self.__possibilities)):
            options.append(nextcord.SelectOption(label=f"{answer + 1}. Answer",
                                                 description=self.__possibilities[answer][1]))

        options.append(nextcord.SelectOption(label=f"Abstain",
                                             description=f"No Answer"))

        super().__init__(placeholder=f"Answer", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        user = interaction.user
        answer = 10

        if self.values[0][0:2] == "1.":
            answer = 0
        elif self.values[0][0:2] == "2.":
            answer = 1
        elif self.values[0][0:2] == "3.":
            answer = 2
        elif self.values[0][0:2] == "4.":
            answer = 3

        votes = list(db.PollVote.select().where(
            db.PollVote.poll_id == self.__message.id,
            db.PollVote.user == user.id
        ))

        if len(votes) == 0:
            db.PollVote.create(user=user.id, poll_id=self.__message.id, answer_id=answer)
            await self.update()
        else:
            db.PollVote.delete().where(
                db.PollVote.user_id == user.id,
                db.PollVote.poll_id == self.__message.id
            ).execute()
            db.PollVote.create(user=user.id, poll_id=self.__message.id, answer_id=answer)

            await self.update()

    async def update(self):
        title = self.__question
        text = ""

        if title[-1] != "?":
            title += "?"

        index = 0
        for possibility in self.__possibilities:
            submits = list(db.PollVote.select().where(
                db.PollVote.poll_id == self.__message.id,
                db.PollVote.answer_id == index
            ))

            text += f"{possibility[0]}: {possibility[1]} **({len(submits)})**\n"
            index += 1

        embed = nextcord.Embed(title=title, description=text, timestamp=datetime.now(),
                               color=nextcord.Colour.blue())
        embed.set_author(name=self.__author.name, icon_url=self.__author.avatar)
        embed.set_footer(text="ㅤ" * 22)
        await self.__message.edit(embed=embed)
