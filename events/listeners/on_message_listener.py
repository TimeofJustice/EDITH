import re
from typing import Optional

import enchant
import nextcord

import events.listener


class Listener(events.listener.Listener):
    """
    A class that listens for messages and handles them accordingly.
    """

    def __init__(self, bot_instance, data: Optional[dict] = None):
        """
        Initializes a new instance of the Listener class.

        :param bot_instance: The instance of the bot.
        :param data: Optional data to use to initialize the instance.
        """
        super().__init__(bot_instance, data)

    async def call(self, message: nextcord.Message):
        """
        Called when a message is received.

        :param message: The message that was received.

        :return: None
        """
        guild = message.guild
        channel = message.channel
        author = message.author

        if guild is not None:
            # Get the guild settings from the database
            guild_settings = \
                self.__mysql.select(table="guilds",
                                    colms="guilds.id, settings.messages_channel, settings.id AS settings_id",
                                    clause=f"INNER JOIN settings ON guilds.settings=settings.id "
                                           f"WHERE guilds.id={guild.id}")[
                    0]

            if guild_settings["messages_channel"] is not None and not author.bot:
                # Get the messages channel
                messages_channel = guild.get_channel(guild_settings["messages_channel"])

                if messages_channel is None:
                    # If the messages channel doesn't exist, remove it from the database
                    self.__mysql.update(table="settings", value=f"log_category=Null",
                                        clause=f"WHERE id='{guild_settings['settings_id']}'")
                    self.__mysql.update(table="settings", value=f"messages_channel=Null",
                                        clause=f"WHERE id='{guild_settings['settings_id']}'")
                    self.__mysql.update(table="settings", value=f"logging_level=0",
                                        clause=f"WHERE id='{guild_settings['settings_id']}'")

                    return

                # Create an embed for the message
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
                    # Add any attachments to the embed
                    for attachment in message.attachments:
                        attachments = f"Name: {attachment.filename}\n" \
                                      f"URL: {attachment.url}\n\n"

                        embed.add_field(name="Attachment", value=attachments, inline=False)
                        embed.set_image(url=attachment.url)

                # Send the message to the messages channel
                await messages_channel.send(embed=embed)

            if not author.bot:
                # Update the user's profile if the message has a high enough percentage of valid words
                if 80 < self.__get_valid_word_percentage(message.content):
                    self.__mysql.update(table="user_profiles", value="messages_send=messages_send+1",
                                        clause=f"WHERE id={author.id}")
                    self.__mysql.update(table="user_profiles", value="messages_daily=messages_daily+1",
                                        clause=f"WHERE id={author.id}")
                    self.__mysql.update(table="user_profiles", value="messages_weekly=messages_weekly+1",
                                        clause=f"WHERE id={author.id}")

                    self.__bot_instance.check_user_progress(author)

    @staticmethod
    def __get_valid_word_percentage(string: str, dictionaries: Optional[list] = None):
        """
        Finds the percentage of a string that actually exists, using
        one or more dictionaries.

        :param string: The String to check.
        :param dictionaries: A list of dictionaries.
        :return: The percentage of actual words in the string.
        """
        if dictionaries is None:
            # If no dictionaries are specified, use all available dictionaries
            dictionaries = enchant.list_languages()

        # Make a list of dictionary objects
        dictionary_objects = [enchant.Dict(d) for d in dictionaries]

        # Remove all punctuation marks and numbers from the string
        cleaned_string = re.sub(r'[^\w\s]', '', string)

        # Split the string into words
        words = cleaned_string.split()

        # Count how many words are in the dictionaries
        valid_word_count = sum(1 for word in words if any(d.check(word.lower()) for d in dictionary_objects))

        # Calculate the percentage of valid words
        valid_word_percentage = valid_word_count / (len(words) or 1) * 100

        # Return the percentage
        return valid_word_percentage
