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


class EditModal(nextcord.ui.Modal):
    def __init__(self, poll_id, bot_instance, guild):
        self.__guild = guild
        self.__bot_instance = bot_instance
        self.__poll = db.Instance.get(id=poll_id)
        self.__poll_data = json.loads(self.__poll.data)
        super().__init__(f"Poll")

        self.__question = nextcord.ui.TextInput(label=f"Whats your question?", style=nextcord.TextInputStyle.short,
                                                placeholder=f"Question?", required=True)

        self.__question.default_value = self.__poll_data["question"]

        self.add_item(self.__question)
        self.__possibilities = []

        for i in range(0, len(self.__poll_data["possibilities"])):
            possibility = nextcord.ui.TextInput(label=f"{i + 1}. Answer",
                                                style=nextcord.TextInputStyle.short,
                                                placeholder=f"Answer",
                                                required=True)

            possibility.default_value = self.__poll_data["possibilities"][i][1]

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

        self.__poll.data = json.dumps(data)
        self.__poll.save()

        session = db.Instance.get(id=self.__poll.id)

        command = instance.Instance(view_callback=View, bot_instance=self.__bot_instance)
        await command.initiate(session)


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__vote = Button(label="Vote", emoji="🗳️",
                             row=1, args=(),
                             style=nextcord.ButtonStyle.primary, callback=self.__callback_vote)

        self.__info = Button(label="ℹ️",
                             row=1, args=(),
                             style=nextcord.ButtonStyle.green, callback=self.__callback_info)

        self.__edit = Button(label="📝",
                             row=1, args=(),
                             style=nextcord.ButtonStyle.green, callback=self.__callback_edit)

        self.__close = Button(label="🗑️",
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
        poll_data = json.loads(db.Instance.get(id=self.__message.id).data)

        self.__dropdown = PollDropdown(poll_data["possibilities"], poll_data["question"],
                                       self.__message, self.__author, self.__bot_instance)

        self.clear_items()
        self.add_item(self.__dropdown)
        self.add_item(self.__vote)
        self.add_item(self.__info)
        self.add_item(self.__edit)
        self.add_item(self.__close)

        text = ""

        index = 0
        for possibility in poll_data["possibilities"]:
            submits = list(db.PollVote.select().where(
                db.PollVote.poll_id == self.__message.id,
                db.PollVote.answer_id == index
            ))

            text += f"{possibility[0]}: {possibility[1]} **({len(submits)})**\n"
            index += 1

        text += f"Abstain: No Answer **({len(list(db.PollVote.select().where(db.PollVote.poll_id == self.__message.id, db.PollVote.answer_id == 10)))})**\n"

        embed = nextcord.Embed(title=poll_data["question"], description=text, timestamp=datetime.now(),
                               color=nextcord.Colour.blue())
        embed.set_author(name=self.__author.name, icon_url=self.__author.avatar)
        embed.set_footer(text="ㅤ" * 22)
        await self.__message.edit(content="", embed=embed, view=self)

    async def __update(self):
        poll_data = json.loads(db.Instance.get(id=self.__message.id).data)

        title = poll_data["question"]
        text = ""

        if title[-1] != "?":
            title += "?"

        index = 0
        for possibility in poll_data["possibilities"]:
            submits = list(db.PollVote.select().where(
                db.PollVote.poll_id == self.__message.id,
                db.PollVote.answer_id == index
            ))

            text += f"{possibility[0]}: {possibility[1]} **({len(submits)})**\n"
            index += 1

        text += f"Abstain: No Answer **({len(list(db.PollVote.select().where(db.PollVote.poll_id == self.__message.id, db.PollVote.answer_id == 10)))})**\n"

        embed = nextcord.Embed(title=title, description=text, timestamp=datetime.now(),
                               color=nextcord.Colour.blue())
        embed.set_author(name=self.__author.name, icon_url=self.__author.avatar)
        embed.set_footer(text="ㅤ" * 22)
        await self.init()

    async def __callback_vote(self, interaction: nextcord.Interaction, args):
        user = interaction.user
        answer = 10

        if len(self.__dropdown.values) == 0:
            await interaction.response.send_message("You have to select an answer.", ephemeral=True)
            return

        if self.__dropdown.values[0][0:2] == "1.":
            answer = 0
        elif self.__dropdown.values[0][0:2] == "2.":
            answer = 1
        elif self.__dropdown.values[0][0:2] == "3.":
            answer = 2
        elif self.__dropdown.values[0][0:2] == "4.":
            answer = 3

        votes = list(db.PollVote.select().where(
            db.PollVote.poll_id == self.__message.id,
            db.PollVote.user == user.id
        ))

        if len(votes) == 0:
            db.PollVote.create(user=user.id, poll_id=self.__message.id, answer_id=answer)
            await self.__update()
        else:
            db.PollVote.delete().where(
                db.PollVote.user_id == user.id,
                db.PollVote.poll_id == self.__message.id
            ).execute()
            db.PollVote.create(user=user.id, poll_id=self.__message.id, answer_id=answer)

            await self.__update()

    async def __callback_info(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, True):
            poll_data = json.loads(db.Instance.get(id=self.__message.id).data)

            text = ""

            index = 0
            for possibility in poll_data["possibilities"]:
                submits = list(db.PollVote.select().where(
                    db.PollVote.poll_id == self.__message.id,
                    db.PollVote.answer_id == index
                ))

                text += f"{possibility[0]}: {possibility[1]} **({len(submits)})**\n"

                for submit in submits:
                    user = self.__guild.get_member(int(submit.user.id))
                    text += f"    - {user.display_name}\n"

                index += 1

            text += f"Abstain: No Answer **({len(list(db.PollVote.select().where(db.PollVote.poll_id == self.__message.id, db.PollVote.answer_id == 10)))})**\n"

            for submit in list(db.PollVote.select().where(db.PollVote.poll_id == self.__message.id, db.PollVote.answer_id == 10)):
                user = self.__guild.get_member(int(submit.user.id))
                text += f"    - {user.display_name}\n"

            embed = nextcord.Embed(title=poll_data["question"], description=text, timestamp=datetime.now(),
                                   color=nextcord.Colour.blue())

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("You are not the author of this poll.", ephemeral=True)

    async def __callback_edit(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, True):
            await interaction.response.send_modal(EditModal(poll_id=self.__message.id, bot_instance=self.__bot_instance, guild=self.__guild))
        else:
            await interaction.response.send_message("You are not the author of this poll.", ephemeral=True)

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
        pass
