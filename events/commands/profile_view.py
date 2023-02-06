import urllib.request
from datetime import datetime
import json
import random
from math import floor
from colorthief import ColorThief

import nextcord

from events import view
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        if instance_data is None:
            instance_data = {}

        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__profile_button = Button(label="👤 Profile", row=0, args=("profile",),
                                       style=nextcord.ButtonStyle.blurple, callback=self.__callback_profile)
        self.__back_button = Button(label="↩ Back", row=0, args=("back",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_back)
        self.__prev_button = Button(label="◀", row=0, args=("prev",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_prev)
        self.__overview_button = Button(label="📑 Overview", row=0, args=("overview",),
                                        style=nextcord.ButtonStyle.blurple, callback=self.__callback_achievements)
        self.__next_button = Button(label="▶", row=0, args=("next",),
                                    style=nextcord.ButtonStyle.grey, callback=self.__callback_next)
        self.__tasks_button = Button(label="📋 Tasks", row=0, args=("tasks",),
                                     style=nextcord.ButtonStyle.blurple, callback=self.__callback_tasks)
        self.__achievements_button = Button(label="🏆 Achievements", row=0, args=("achievements",),
                                            style=nextcord.ButtonStyle.blurple, callback=self.__callback_achievements)
        self.__close_button = Button(label="❌ Close", row=0, args=("close",),
                                     style=nextcord.ButtonStyle.red, callback=self.__callback_close)

        self.add_item(self.__profile_button)

        if self.__instance_data["user"] == self.__author.id:
            self.add_item(self.__tasks_button)

        self.add_item(self.__achievements_button)
        self.add_item(self.__close_button)

    async def init(self):
        await self.__callback_profile()

    async def __callback_profile(self, interaction: nextcord.Interaction = None, args=None):
        if interaction is None or self.__is_author(interaction):
            self.__profile_button.style = nextcord.ButtonStyle.green
            self.__profile_button.disabled = True
            self.__tasks_button.style = nextcord.ButtonStyle.blurple
            self.__tasks_button.disabled = False
            self.__achievements_button.style = nextcord.ButtonStyle.blurple
            self.__achievements_button.disabled = False

            member = self.__guild.get_member(int(self.__instance_data["user"]))
            level = 0
            time_in_voice = 0
            messages = 0
            rand = random.Random()
            achievements = rand.randint(0, 100)
            xp_left = 1000

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
            embed.set_footer(text="ㅤ" * 33)

            await self.__message.edit(content="", embed=embed, view=self, attachments=[])

    async def __callback_tasks(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__profile_button.style = nextcord.ButtonStyle.blurple
            self.__profile_button.disabled = False
            self.__tasks_button.style = nextcord.ButtonStyle.green
            self.__tasks_button.disabled = True
            self.__achievements_button.style = nextcord.ButtonStyle.blurple
            self.__achievements_button.disabled = False

            member = self.__guild.get_member(int(self.__instance_data["user"]))
            daily_voice_session = []
            daily_message_session = []
            daily_voice = 0
            daily_messages = 0

            if 0 < len(daily_voice_session):
                daily_voice = floor(daily_voice_session[0])

            if 0 < len(daily_message_session):
                daily_messages = daily_message_session[0]

            embed = nextcord.Embed(
                title=f"**{member.display_name}'s daily tasks**",
                colour=nextcord.Colour.purple()
            )

            tasks = ["None", "None"]

            embed.add_field(
                name="Daily tasks",
                value=f"- {tasks[0]}\n"
                      f"- {tasks[1]}"
            )

            embed.add_field(
                name="\u200b",
                value="\u200b",
                inline=False
            )

            embed.add_field(name="Daily voice-time",
                            value=f"{daily_voice} / 180 minutes")

            embed.add_field(
                name="\u200b",
                value="\u200b"
            )

            embed.add_field(name="Daily messages",
                            value=f"{daily_messages} / 100 messages")

            embed.set_thumbnail(url=member.display_avatar)
            embed.set_footer(text="ㅤ" * 33)

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
            embed.set_footer(text="ㅤ" * 33)

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

            embed.set_footer(text="ㅤ" * 33)

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

            embed.set_footer(text="ㅤ" * 33)

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
