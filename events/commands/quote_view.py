import json
from datetime import datetime
import nextcord

import db
from events import view, instance, command
from events.view import Button


class Modal(nextcord.ui.Modal):
    def __init__(self, from_user, bot_instance, guild):
        self.__guild = guild
        self.__bot_instance = bot_instance
        self.__from_user = from_user
        super().__init__(f"Quote")

        self.__quote = nextcord.ui.TextInput(label=f"Quote",
                                             style=nextcord.TextInputStyle.paragraph,
                                             placeholder=f"What's the quote?",
                                             required=True)

        self.add_item(self.__quote)

        self.__year = nextcord.ui.TextInput(label=f"Year",
                                            style=nextcord.TextInputStyle.short,
                                            placeholder=f"What's the year?",
                                            required=True,
                                            max_length=4,
                                            min_length=4)

        self.add_item(self.__year)

    async def callback(self, interaction: nextcord.Interaction):
        quote = self.__quote.value
        year = self.__year.value

        if self.__from_user.bot:
            await interaction.response.send_message("Bots can't add quotes.", ephemeral=True)
            return

        if not year.isdigit():
            await interaction.response.send_message("Year must be a number.", ephemeral=True)
            return

        db.Quote.create(author=interaction.user.id, user=self.__from_user.id, quote=quote, year=year)

        await interaction.response.send_message("Quote has been added.", ephemeral=True)


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data["method"] == "view":
            await self.view()
        else:
            await self.remove()

    async def view(self):
        if self.__data["quote_id"] is not None:
            if not db.Quote.select().where(db.Quote.id == self.__data["quote_id"]).exists():
                await self.__interaction.response.send_message("Quote does not exist.", ephemeral=True)
                return

            quote = db.Quote.get(db.Quote.id == self.__data["quote_id"])
        else:
            if not db.Quote.select().exists():
                await self.__interaction.response.send_message("No quotes exist.", ephemeral=True)
                return

            quote = db.Quote.select().order_by(db.fn.Random()).limit(1).get()

        from_user = await self.__guild.fetch_member(quote.user)

        if quote.author is not None:
            author_user = await self.__guild.fetch_member(quote.author)
        else:
            author_user = None

        text = f"\"{quote.quote}\" - {quote.year}"

        embed = nextcord.Embed(
            description=text,
            colour=nextcord.Colour.random()
        )

        if from_user is not None:
            embed.set_author(name=from_user.display_name, icon_url=from_user.avatar.url)
        else:
            embed.set_author(name="Unknown User")

        if author_user is not None:
            embed.set_footer(text=f"#{quote.id} added by {author_user.display_name}")
        else:
            embed.set_footer(text=f"#{quote.id} added by Unknown User")

        await self.__interaction.response.send_message(embed=embed)

    async def remove(self):
        quote_id = self.__data["quote_id"]

        if not db.Quote.select().where(db.Quote.id == quote_id).exists():
            await self.__interaction.response.send_message("Quote does not exist.", ephemeral=True)
            return

        db.Quote.delete().where(db.Quote.id == quote_id).execute()

        await self.__interaction.response.send_message("Quote has been removed.", ephemeral=True)
