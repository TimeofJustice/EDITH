import nextcord

from events import command, view
from events.view import Button


class View(view.View):
    def __init__(self, author, guild, channel, message, bot_instance, instance_data=None):
        if instance_data is None:
            instance_data = {}

        super().__init__(author, guild, channel, message, bot_instance, instance_data)

        self.__add_button = Button(label="📥 Add", row=0, args=("add",),
                                   style=nextcord.ButtonStyle.green, callback=self.__callback_stop)
        self.__voice_button = Button(label="🔊 Only voice", row=0, args=("voice",),
                                     style=nextcord.ButtonStyle.blurple, callback=self.__callback_stop)
        self.__block_button = Button(label="⛔ Block", row=0, args=("block",),
                                     style=nextcord.ButtonStyle.red, callback=self.__callback_stop)

        self.add_item(self.__add_button)
        self.add_item(self.__voice_button)
        self.add_item(self.__block_button)

    async def init(self):
        embed = nextcord.Embed(
            description=f"{self.__author.display_name} is waiting!",
            colour=nextcord.Colour.purple()
        )

        embed.add_field(
            name="📥 Add",
            value="Grants access to the room until the user is removes manually!",
            inline=True
        )
        embed.add_field(
            name="🔊 Only voice",
            value="Grants access to the voice-channel until the user lefts!",
            inline=True
        )
        embed.add_field(
            name="⛔ Block",
            value="Denied all future interactions with this room until the user gets unblocked!",
            inline=True
        )

        embed.set_author(
            name="Smart Channel Manager",
            icon_url="https://images-ext-2.discordapp.net/external/"
                     "Ca6iHCDtx2yG5aw9ZAF6Ja-kJezcUu_N24TULp6Q9bc/https/cdn0.iconfinder.com/data/"
                     "icons/small-n-flat/24/678136-shield-warning-512.png"
        )

        await self.__message.edit(content="", embed=embed, view=self)

    async def __callback_stop(self, interaction: nextcord.Interaction, args):
        if self.__is_author(interaction, exception_owner=True):
            self.__stop_button.label = "❌ Stopping..."
            await self.__message.edit(view=self)

            await interaction.response.defer()

            self.__mysql.delete(table="instances", clause=f"WHERE message_id={self.__message.id}")

            embed = nextcord.Embed(
                title="TTS stopped!",
                description="See you next time!",
                colour=nextcord.Colour.orange()
            )

            await self.__message.edit(content="", embed=embed, view=None)

        return args
