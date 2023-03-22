import nextcord
import requests

from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        resp = requests.get(f"https://some-random-api.ml/animal/{self.__data['animal']}")

        if 300 > resp.status_code >= 200:
            content = resp.json()

            embed = nextcord.Embed(
                title="Animals!",
                description=f"{content['fact']}",
                colour=nextcord.Colour.random()
            )

            embed.set_image(url=content['image'])
        else:
            embed = nextcord.Embed(
                title="Error!",
                description=f"`Unknown error`",
                colour=nextcord.Colour.orange()
            )

        await self.__interaction.send(embed=embed, ephemeral=True)
