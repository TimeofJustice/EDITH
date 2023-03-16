import nextcord

from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        owner = await self.__bot.fetch_user(243747656470495233)

        embed = nextcord.Embed(
            title="About E.D.I.T.H!",
            description=f"I am **E.D.I.T.H**, I am the 4. generation of the bot from {owner.mention}.\n"
                        f"\n"
                        f"Developed in **Python** via **nextcord**.\n"
                        f"I am the version **{self.__bot_instance.get_version()}**!",
            colour=nextcord.Colour.random()
        )

        await self.__interaction.send(embed=embed, ephemeral=True)
