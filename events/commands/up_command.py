import nextcord

from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        text = f"Online since {self.__bot_instance.get_running_time()}!"
        msg = nextcord.Embed(
            title="",
            description=text,
            color=nextcord.Colour.gold()
        )

        await self.__interaction.send(embed=msg, ephemeral=True)
