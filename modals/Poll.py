from datetime import datetime
import nextcord
from nextcord import ui


class Poll(ui.Modal):
    def __init__(self, questions):
        super().__init__("Test")

        self.__question = ui.TextInput(label="Was ist deine Frage?", style=nextcord.TextInputStyle.short, placeholder="Frage", required=True)
        self.add_item(self.__question)
        self.__possibilities = []

        reacts = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

        for i in range(0, questions):
            possibility = ui.TextInput(label=f"{i + 1}. Antwort",
                                       style=nextcord.TextInputStyle.short,
                                       placeholder="Antwort",
                                       required=True)

            self.__possibilities.append(
                [possibility, reacts[i]]
            )

            self.add_item(possibility)

    async def callback(self, interaction: nextcord.Interaction):
        channel = interaction.channel

        title = self.__question.value
        text = ""

        if title[-1] != "?":
            title += "?"

        for possibility in self.__possibilities:
            text += f"{possibility[1]} {possibility[0].value}\n"

        embed = nextcord.Embed(title=title, description=text, timestamp=datetime.now(), color=nextcord.Colour.blue())
        msg = await channel.send(embed=embed)

        for possibility in self.__possibilities:
            await msg.add_reaction(possibility[1])

        await interaction.response.send_message(content="Wurde angelegt", ephemeral=True)
