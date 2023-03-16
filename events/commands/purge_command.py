import math
import nextcord

from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        channel = self.__interaction.channel

        limit = self.__data["amount"]
        x = limit
        x_h = math.floor(x / 100)
        x_r = x % 100

        embed = nextcord.Embed(
            description=f"Trying to delete {limit} messages!",
            color=nextcord.Colour.purple()
        )
        await self.__interaction.send(embed=embed, ephemeral=True)

        messages = await channel.purge(limit=x_h * 100)
        messages_ = await channel.purge(limit=x_r)
        messages.extend(messages_)

        embed = nextcord.Embed(
            description=f"{len(messages)} messages deleted!",
            color=nextcord.Colour.purple()
        )

        embed.set_image(url="attachment://purged.gif")

        with open('data/pics/purged.gif', 'rb') as fp:
            await self.__interaction.edit_original_message(embed=embed,
                                                           file=nextcord.File(fp, 'purged.gif'))
