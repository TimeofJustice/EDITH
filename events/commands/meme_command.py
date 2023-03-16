import json
import nextcord
import requests

from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        api_url_base = "https://meme-api.com/gimme"

        author = self.__interaction.user
        subreddit = self.__data.get('subreddit')

        if subreddit is not None:
            response = requests.get(f"{api_url_base}/{self.__data.get('subreddit')}")
        else:
            response = requests.get(f"{api_url_base}/")

        if response.status_code == 200:
            api_data = json.loads(response.content.decode("utf-8"))
        else:
            api_data = None

        if api_data is not None:
            embed = nextcord.Embed(
                title=api_data["title"],
                description=api_data["subreddit"]
            )

            embed.set_image(url=api_data["url"])
            embed.set_author(name=author.display_name)

            await self.__interaction.send(embed=embed)

            message = await self.__interaction.original_message()

            await message.add_reaction("👍")
            await message.add_reaction("👎")
        else:
            embed = nextcord.Embed(
                description="This subreddit doesn't have any memes",
                colour=nextcord.Colour.orange()
            )

            await self.__interaction.send(embed=embed, ephemeral=True)
