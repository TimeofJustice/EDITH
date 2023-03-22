import nextcord

import db
import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, payload: nextcord.RawMessageDeleteEvent):
        guild = self.__bot.get_guild(payload.guild_id)

        if guild is not None:
            channel = guild.get_channel(payload.channel_id)

            guild_data = db.Guild.get_or_none(db.Guild.id == guild.id)

            if guild_data.settings.messages_channel is not None and channel.id != guild_data.settings.messages_channel:
                messages_channel = guild.get_channel(guild_data.settings.messages_channel)

                embed = nextcord.Embed(
                    color=nextcord.Colour.red()
                )

                embed.set_author(name=f"Message deleted (ID:{payload.message_id})")

                embed.add_field(name="Channel",
                                value=f"**Category:** {channel.category}\n"
                                      f"**Channel:** {channel} (ID:{channel.id})")

                await messages_channel.send(embed=embed)
