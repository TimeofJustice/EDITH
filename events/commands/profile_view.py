from datetime import datetime
import json
import random
from math import floor
import schedule
import nextcord

from events import view
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        # Potenzielles Refactoring
        # self.__buttons = {
        #     "profile": Button(label="Profile", emoji="👤", row=0, args=("profile",),
        #                       style=nextcord.ButtonStyle.blurple, callback=self.__callback_profile),
        #     "back": Button(label="Back", emoji="↩", row=0, args=("back",),
        #                    style=nextcord.ButtonStyle.grey, callback=self.__callback_back),
        #     "prev": Button(label="", emoji="◀", row=0, args=("prev",),
        #                    style=nextcord.ButtonStyle.grey, callback=self.__callback_prev),
        #     "overview": Button(label="Overview", emoji="📑", row=0, args=("overview",),
        #                        style=nextcord.ButtonStyle.blurple, callback=self.__callback_achievements),
        #     "next": Button(label="", emoji="▶", row=0, args=("next",),
        #                    style=nextcord.ButtonStyle.grey, callback=self.__callback_next),
        #     "tasks": Button(label="Tasks", emoji="📋", row=0, args=("tasks",),
        #                     style=nextcord.ButtonStyle.blurple, callback=self.__callback_tasks),
        #     "achievements": Button(label="Achievements", emoji="🏆", row=0, args=("achievements",),
        #                            style=nextcord.ButtonStyle.blurple, callback=self.__callback_achievements),
        #     "close": Button(label="Close", emoji="❌", row=0, args=("close",),
        #                     style=nextcord.ButtonStyle.red, callback=self.__callback_close)
        # }
        #
        # self.add_item(self.__buttons["profile"])
        #
        # if self.__instance_data.get("user") == author.id:
        #     self.add_item(self.__buttons["tasks"])
        #
        # self.add_item(self.__buttons["achievements"])
        # self.add_item(self.__buttons["close"])

        self.__profile_button = Button(label="Profile", emoji="👤", row=0, args=("profile",),
                                       style=nextcord.ButtonStyle.blurple, callback=self.__callback_profile)
        self.__back_button = Button(label="Back", emoji="↩", row=0, args=("back",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_back)
        self.__prev_button = Button(label="", emoji="◀", row=0, args=("prev",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_prev)
        self.__overview_button = Button(label="Overview", emoji="📑", row=0, args=("overview",),
                                        style=nextcord.ButtonStyle.blurple, callback=self.__callback_achievements)
        self.__next_button = Button(label="", emoji="▶", row=0, args=("next",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_next)
        self.__tasks_button = Button(label="Tasks", emoji="📋", row=0, args=("tasks",),
                                     style=nextcord.ButtonStyle.blurple, callback=self.__callback_tasks)
        self.__achievements_button = Button(label="Achievements", emoji="🏆", row=0, args=("achievements",),
                                            style=nextcord.ButtonStyle.blurple, callback=self.__callback_achievements)
        self.__close_button = Button(label="Close", emoji="❌", row=0, args=("close",),
                                     style=nextcord.ButtonStyle.red, callback=self.__callback_close)

        self.add_item(self.__profile_button)

        if self.__instance_data["user"] == self.__author.id:
            self.add_item(self.__tasks_button)

        self.add_item(self.__achievements_button)
        self.add_item(self.__close_button)

    async def init(self, **kwargs):
        self.__bot_instance.create_user_profile(self.__author)
        await self.__callback_profile()

    async def __callback_profile(self, interaction: nextcord.Interaction = None, args=None):
        if interaction is None or self.__is_author(interaction):
            self.__profile_button.style = nextcord.ButtonStyle.green
            self.__profile_button.disabled = True
            self.__tasks_button.style = nextcord.ButtonStyle.blurple
            self.__tasks_button.disabled = False
            self.__achievements_button.style = nextcord.ButtonStyle.blurple
            self.__achievements_button.disabled = False

            user_profile = self.__mysql.select(table="user_profiles", colms="*",
                                               clause=f"WHERE id={self.__instance_data['user']}")[0]

            member = self.__guild.get_member(int(self.__instance_data["user"]))
            xp = user_profile["xp"]
            xp_data = self.__get_level(xp)
            level = xp_data[0]
            time_in_voice = user_profile["time_in_voice"]
            messages = user_profile["messages_send"]
            rand = random.Random()
            achievements = rand.randint(0, 100)
            xp_left = xp_data[1]

            embed = nextcord.Embed(
                title=f"**{member.display_name}'s profile**",
                colour=nextcord.Colour.purple()
            )

            embed.add_field(name="Level",
                            value=f"Level {level}\n"
                                  f"*{xp_left} XP left*")

            achies = floor(achievements / 10)
            lefts = 10 - achies

            embed.add_field(name="Achievements",
                            value=f"{achievements} / {100}\n"
                                  f"[{'▮' * achies}{'▯' * lefts}]")

            embed.add_field(
                name="\u200b",
                value="\u200b",
                inline=False
            )

            embed.add_field(name="Time in voice-channel",
                            value=f"{time_in_voice} minutes")

            embed.add_field(name="Sent messages",
                            value=f"{messages} messages")

            embed.set_thumbnail(url=member.display_avatar)

            await self.__message.edit(content="", embed=embed, view=self, attachments=[])

    async def __callback_tasks(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__profile_button.style = nextcord.ButtonStyle.blurple
            self.__profile_button.disabled = False
            self.__tasks_button.style = nextcord.ButtonStyle.green
            self.__tasks_button.disabled = True
            self.__achievements_button.style = nextcord.ButtonStyle.blurple
            self.__achievements_button.disabled = False

            user_profile = self.__mysql.select(table="user_profiles", colms="*",
                                               clause=f"WHERE id={self.__instance_data['user']}")[0]

            member = self.__guild.get_member(int(self.__instance_data["user"]))

            tasks_timers = schedule.get_jobs('tasks')

            embed = nextcord.Embed(
                title=f"**{member.display_name}'s tasks**",
                colour=nextcord.Colour.purple()
            )

            daily_tasks = json.loads(user_profile["tasks_daily"])
            weekly_tasks = json.loads(user_profile["tasks_weekly"])

            for daily_task in daily_tasks:
                progress = 0
                complete = "⭕"

                if daily_task["accomplish_type"] == "minutes_in_voice":
                    progress = user_profile["voice_daily"]
                elif daily_task["accomplish_type"] == "send_messages":
                    progress = user_profile["messages_daily"]
                elif daily_task["accomplish_type"] == "movle_game":
                    progress = user_profile["movle_daily"]

                if daily_task["completed"]:
                    complete = "🟢"
                    progress = daily_task["amount"]

                daily_task.update({
                    "complete": complete,
                    "progress": progress
                })

            for weekly_task in weekly_tasks:
                progress = 0
                complete = "⭕"

                if weekly_task["accomplish_type"] == "minutes_in_voice":
                    progress = user_profile["voice_weekly"]
                elif weekly_task["accomplish_type"] == "send_messages":
                    progress = user_profile["messages_weekly"]
                elif weekly_task["accomplish_type"] == "movle_game":
                    progress = user_profile["movle_weekly"]

                if weekly_task["completed"]:
                    complete = "🟢"
                    progress = weekly_task["amount"]

                weekly_task.update({
                    "complete": complete,
                    "progress": progress
                })

            embed.add_field(
                name="Daily tasks",
                value=f"{daily_tasks[0]['complete']} {daily_tasks[0]['description']}\n"
                      f"ㅤ\u0020**({daily_tasks[0]['progress']} / {daily_tasks[0]['amount']})**"
                      f"ㅤ*{daily_tasks[0]['xp']} XP*\n"
                      f"{daily_tasks[1]['complete']} {daily_tasks[1]['description']}\n"
                      f"ㅤ\u0020**({daily_tasks[1]['progress']}  / {daily_tasks[1]['amount']})**"
                      f"ㅤ*{daily_tasks[1]['xp']} XP*\n\n"
                      f"ㅤ\u0020Reset: <t:{int(tasks_timers[0].next_run.timestamp())}:R>",
                inline=False
            )

            embed.add_field(
                name="Weekly tasks",
                value=f"{weekly_tasks[0]['complete']} {weekly_tasks[0]['description']}\n"
                      f"ㅤ\u0020**({weekly_tasks[0]['progress']} / {weekly_tasks[0]['amount']})**"
                      f"ㅤ*{weekly_tasks[0]['xp']} XP*\n"
                      f"{weekly_tasks[1]['complete']} {weekly_tasks[1]['description']}\n"
                      f"ㅤ\u0020**({weekly_tasks[1]['progress']} / {weekly_tasks[1]['amount']})**"
                      f"ㅤ*{weekly_tasks[1]['xp']} XP*\n\n"
                      f"ㅤ\u0020Reset: <t:{int(tasks_timers[1].next_run.timestamp())}:R>",
                inline=False
            )

            embed.set_thumbnail(url=member.display_avatar)

            await self.__message.edit(content="", embed=embed, view=self, attachments=[])

    async def __callback_achievements(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.clear_items()
            self.add_item(self.__back_button)
            self.add_item(self.__prev_button)
            self.add_item(self.__overview_button)
            self.add_item(self.__next_button)
            self.add_item(self.__close_button)

            self.__overview_button.style = nextcord.ButtonStyle.green
            self.__overview_button.disabled = True
            self.__prev_button.disabled = True
            self.__next_button.disabled = False

            self.__instance_data["achievement_index"] = None

            self.__mysql.update(table="instances", value=f"data='{json.dumps(self.__instance_data)}'",
                                clause=f"WHERE message_id={self.__message.id}")

            member = self.__guild.get_member(int(self.__instance_data["user"]))
            achievements = 10

            embed = nextcord.Embed(
                title=f"**{member.display_name}'s achievements**",
                colour=nextcord.Colour.purple(),
                description=f"You have accomplished {achievements} \n"
                            f"achievements on supported servers!"
            )

            rarest_title = "None"
            commons_title = "None"
            rarest_perc = 0
            commons_perc = 0

            embed.add_field(name="Rarest achievement",
                            value=f"{rarest_title} ({rarest_perc}%)",
                            inline=False)

            embed.add_field(name="Commons achievement",
                            value=f"{commons_title} ({commons_perc}%)",
                            inline=False)

            achies = floor(achievements / 10)
            lefts = 10 - achies

            embed.add_field(name="Achievements",
                            value=f"{achievements} / {100}\n"
                                  f"[{'▮' * achies}{'▯' * lefts}]",
                            inline=False)

            embed.set_thumbnail(url=member.display_avatar)

            if achievements == 0:
                self.__next_button.disabled = True

            await self.__message.edit(content="", embed=embed, view=self, attachments=[])

    async def __callback_next(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__next_button.disabled = False
            self.__prev_button.disabled = False
            self.__overview_button.style = nextcord.ButtonStyle.blurple
            self.__overview_button.disabled = False
            achievements = 0

            if self.__instance_data["achievement_index"] is not None:
                self.__instance_data["achievement_index"] = self.__instance_data["achievement_index"] + 1
            else:
                self.__instance_data["achievement_index"] = 0

            self.__mysql.update(table="instances", value=f"data='{json.dumps(self.__instance_data)}'",
                                clause=f"WHERE message_id={self.__message.id}")

            if self.__instance_data["achievement_index"] == achievements:
                self.__next_button.disabled = True

            if self.__instance_data["achievement_index"] == 0:
                self.__prev_button.disabled = True

            member = self.__guild.get_member(int(self.__instance_data["user"]))
            achievement = "None"
            achievement_desc = "None"
            achievement_date = datetime.strptime("2022/06/12 20:15", "%Y/%m/%d %H:%M")
            achievement_rarity = 0

            embed = nextcord.Embed(
                title=f"**{achievement} ({achievement_date})**",
                colour=nextcord.Colour.purple(),
                description=f"{achievement_desc}\n\n"
                            f"*{achievement_rarity}% from all users*"
            )

            rarities = ["common", "uncommon", "rare", "legendary"]
            rarity = random.choice(rarities)

            embed.set_thumbnail(url=f"attachment://{rarity}.png")

            with open(f'data/pics/{rarity}.png', 'rb') as fp:
                await self.__message.edit(content="", embed=embed, view=self, file=nextcord.File(fp, f'{rarity}.png'))

    async def __callback_prev(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__next_button.disabled = False
            self.__prev_button.disabled = False
            self.__overview_button.style = nextcord.ButtonStyle.blurple
            self.__overview_button.disabled = False

            self.__instance_data["achievement_index"] = self.__instance_data["achievement_index"] - 1

            self.__mysql.update(table="instances", value=f"data='{json.dumps(self.__instance_data)}'",
                                clause=f"WHERE message_id={self.__message.id}")

            if self.__instance_data["achievement_index"] == 0:
                self.__prev_button.disabled = True

            member = self.__guild.get_member(int(self.__instance_data["user"]))
            achievement = "None"
            achievement_desc = "None"
            achievement_date = datetime.strptime("2022/06/12 20:15", "%Y/%m/%d %H:%M")
            achievement_rarity = 0

            embed = nextcord.Embed(
                title=f"**{achievement} ({achievement_date})**",
                colour=nextcord.Colour.purple(),
                description=f"{achievement_desc}\n\n"
                            f"*{achievement_rarity}% from all users*"
            )

            rarities = ["common", "uncommon", "rare", "legendary"]
            rarity = random.choice(rarities)

            embed.set_thumbnail(url=f"attachment://{rarity}.png")

            with open(f'data/pics/{rarity}.png', 'rb') as fp:
                await self.__message.edit(content="", embed=embed, view=self, file=nextcord.File(fp, f'{rarity}.png'))

    async def __callback_back(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.clear_items()
            self.add_item(self.__profile_button)
            self.add_item(self.__tasks_button)
            self.add_item(self.__achievements_button)
            self.add_item(self.__close_button)

            await self.__callback_profile()

    async def __callback_close(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")
            await self.__message.delete()

    @staticmethod
    def __get_level(xp, base_xp=1000, xp_multiplier=1.1):
        """
        Gibt das Level und die benötigte XP bis zum nächsten Level zurück, basierend auf einer gegebenen Menge an XP.

        :param xp: Die Menge an XP, für die das Level berechnet werden soll.
        :param base_xp: Die Basis-XP, die für das Erreichen des Level 1 benötigt werden. Standardmäßig 1000.
        :param xp_multiplier: Der Multiplikator, der bestimmt, wie viel XP für jedes Level benötigt werden. Standardmäßig 1.1.
        :return: Ein Tupel aus dem aktuellen Level und der benötigten XP bis zum nächsten Level.
        """
        # Initialisiere das Level auf 0
        level = 0

        # Schleife durch jedes Level, beginnend bei Level 1
        while xp >= base_xp:
            # Erhöhe das Level um 1
            level += 1

            # Subtrahiere die Basis-XP des aktuellen Levels von der gegebenen XP-Menge
            xp -= base_xp

            # Berechne die benötigte XP für das nächste Level
            base_xp = round(base_xp * xp_multiplier)

        # Berechne die benötigte XP bis zum nächsten Level
        next_level_xp = base_xp - xp

        # Gib das Level und die benötigte XP bis zum nächsten Level zurück
        return level, next_level_xp

