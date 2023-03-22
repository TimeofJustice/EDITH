import json
import nextcord

import db
from events import view
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        if "term" in self.__instance_data.keys():
            self.__term = self.__instance_data["term"]
        else:
            self.__term = ""

        self.add_item(Button(label="7", row=0, args=("7",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="8", row=0, args=("8",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="9", row=0, args=("9",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="DEL", row=0, args=(),
                             style=nextcord.ButtonStyle.red, callback=self.__callback_del))
        self.add_item(Button(label="AC", row=0, args=(),
                             style=nextcord.ButtonStyle.red, callback=self.__callback_ac))
        self.add_item(Button(label="4", row=1, args=("4",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="5", row=1, args=("5",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="6", row=1, args=("6",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="×", row=1, args=("*",),
                             style=nextcord.ButtonStyle.blurple, callback=self.__callback_add_term))
        self.add_item(Button(label="÷", row=1, args=("/",),
                             style=nextcord.ButtonStyle.blurple, callback=self.__callback_add_term))
        self.add_item(Button(label="1", row=2, args=("1",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="2", row=2, args=("2",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="3", row=2, args=("3",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="+", row=2, args=("+",),
                             style=nextcord.ButtonStyle.blurple, callback=self.__callback_add_term))
        self.add_item(Button(label="-", row=2, args=("-",),
                             style=nextcord.ButtonStyle.blurple, callback=self.__callback_add_term))
        self.add_item(Button(label="0", row=3, args=("0",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label=".", row=3, args=(".",),
                             style=nextcord.ButtonStyle.grey, callback=self.__callback_add_term))
        self.add_item(Button(label="ㅤ", row=3, args=(),
                             style=nextcord.ButtonStyle.grey, disabled=True, callback=None))
        self.add_item(Button(label="ㅤ", row=3, args=(),
                             style=nextcord.ButtonStyle.grey, disabled=True, callback=None))
        self.add_item(Button(label="=", row=3, args=(),
                             style=nextcord.ButtonStyle.green, callback=self.__callback_equals))
        self.add_item(Button(label=f"ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ Close ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ",
                             style=nextcord.ButtonStyle.red, row=4, callback=self.__callback_close, args=()))

    async def init(self, **kwargs):
        author = self.__author
        screen = self.__term.replace("*", "×").replace("/", "÷")

        embed = nextcord.Embed(
            title=f"{author.display_name}'s Calculator",
            description=f"```{screen}|```"
        )
        embed.set_footer(text="ㅤ" * 27)
        await self.__message.edit(content="", embed=embed, view=self)

    async def __sync_screen(self):
        screen = self.__term.replace("*", "×").replace("/", "÷")
        self.__instance_data["term"] = self.__term

        embed = nextcord.Embed(
            title=f"{self.__author.display_name}'s Calculator",
            description=f"```{screen}|```"
        )
        embed.set_footer(text="ㅤ" * 27)

        await self.__message.edit(content="", embed=embed)

        instance = db.Instance.get_or_none(id=self.__message.id)
        instance.data = json.dumps(self.__instance_data)
        instance.save()

    async def __equals(self):
        screen = self.__term.replace("*", "×").replace("/", "÷")

        try:
            result = eval(self.__term)

            embed = nextcord.Embed(
                title=f"{self.__author.display_name}'s Calculator",
                description=f"```{screen}={result}```"
            )
        except Exception as e:
            embed = nextcord.Embed(
                title=f"{self.__author.display_name}'s Calculator",
                description=f"```Unknown Error```",
                color=nextcord.Colour.red()
            )

            print(e)

        embed.set_footer(text="ㅤ" * 27)
        await self.__message.edit(content="", embed=embed)

    async def __callback_add_term(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__term += args[0]
            await self.__sync_screen()

        return args

    async def __callback_del(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__term = self.__term[:-1]
            await self.__sync_screen()

        return args

    async def __callback_ac(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            self.__term = ""
            await self.__sync_screen()

        return args

    async def __callback_equals(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction):
            await self.__equals()

        return args

    async def __callback_close(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            await self.__message.delete()
            instance = db.Instance.get_or_none(id=self.__message.id)
            instance.delete_instance()

        return args
