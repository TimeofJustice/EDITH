import json
import nextcord

import db
from events import view, instance
from events.view import Button


class Modal(nextcord.ui.Modal):
    def __init__(self, news_entry, bot_instance, guild):
        self.__guild = guild
        self.__bot_instance = bot_instance
        self.__news_entry = db.News.get_or_none(db.News.id == news_entry)

        super().__init__(f"{self.__news_entry.name}")

        self.__description = nextcord.ui.TextInput(label=f"What is the description?",
                                                   style=nextcord.TextInputStyle.paragraph,
                                                   placeholder=f"Description", required=True)
        self.add_item(self.__description)

    async def callback(self, interaction: nextcord.Interaction):
        self.__news_entry.description = self.__description.value
        self.__news_entry.save()

        session = self.__news_entry.instance

        command = instance.Instance(view_callback=View, bot_instance=self.__bot_instance)
        await command.initiate(session)

        await interaction.response.send_message("Description updated!", ephemeral=True)


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__news_entry = db.News.get_or_none(db.News.id == self.__instance_data["news_entry"])

        self.add_item(Button(label="Join", row=0, args=(),
                             style=nextcord.ButtonStyle.blurple, callback=self.__callback_join))
        self.add_item(Button(label="Leave", row=0, args=(),
                             style=nextcord.ButtonStyle.red, callback=self.__callback_leave))

    async def init(self, **kwargs):
        title = self.__news_entry.name

        self.__news_entry.instance = self.__message.id
        self.__news_entry.save()

        embed = nextcord.Embed(
            title=f"{title}",
            description=f"{self.__news_entry.description}",
        )
        embed.set_footer(text="ㅤ" * 27)
        await self.__message.edit(content="", embed=embed, view=self)

    async def __callback_join(self, interaction: nextcord.Interaction, args):
        user = interaction.user
        role = self.__guild.get_role(self.__news_entry.role)
        await user.add_roles(role)

        await interaction.response.send_message("You have joined the news channel!", ephemeral=True)

        return args

    async def __callback_leave(self, interaction: nextcord.Interaction, args):
        user = interaction.user
        role = self.__guild.get_role(self.__news_entry.role)
        await user.remove_roles(role)

        await interaction.response.send_message("You have left the news channel!", ephemeral=True)

        return args
