import nextcord

import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(bot_instance, data)

    async def call(self, message: nextcord.Message):
        guild = message.guild
        channel = message.channel
        author = message.author

        if guild is not None:
            guild_settings = \
                self.__mysql.select(table="guilds",
                                    colms="guilds.id, settings.messages_channel, settings.id AS settings_id",
                                    clause=f"INNER JOIN settings ON guilds.settings=settings.id "
                                           f"WHERE guilds.id={guild.id}")[
                    0]

            if guild_settings["messages_channel"] is not None and not author.bot:
                messages_channel = guild.get_channel(guild_settings["messages_channel"])

                embed = nextcord.Embed(
                    color=nextcord.Colour.green(),
                    description=message.content
                )

                embed.set_author(name=f"Message send (ID:{message.id})")
                embed.add_field(name="Author", value=f"**Discord-Name:** {author.name} (ID:{author.id})\n"
                                                     f"**Server-Name:** {author.display_name}")

                embed.add_field(name="Channel",
                                value=f"**Category:** {channel.category}\n"
                                      f"**Channel:** {channel} (ID:{channel.id})")

                if message.attachments:
                    for attachment in message.attachments:
                        attachments = f"Name: {attachment.filename}\n" \
                                      f"URL: {attachment.url}\n\n"

                        embed.add_field(name="Attachment", value=attachments, inline=False)
                        embed.set_image(url=attachment.url)

                await messages_channel.send(embed=embed)

            if not author.bot:
                print("User gained Point")
