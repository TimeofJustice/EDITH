import re
import enchant
import nextcord

import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
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

                if messages_channel is None:
                    self.__mysql.update(table="settings", value=f"log_category=Null",
                                        clause=f"WHERE id='{guild_settings['settings_id']}'")
                    self.__mysql.update(table="settings", value=f"messages_channel=Null",
                                        clause=f"WHERE id='{guild_settings['settings_id']}'")
                    self.__mysql.update(table="settings", value=f"logging_level=0",
                                        clause=f"WHERE id='{guild_settings['settings_id']}'")

                    return

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
                if 80 < self.__get_valid_word_percentage(message.content):
                    self.__mysql.update(table="user_profiles", value="messages_send=messages_send+1",
                                        clause=f"WHERE id={author.id}")
                    self.__mysql.update(table="user_profiles", value="messages_daily=messages_daily+1",
                                        clause=f"WHERE id={author.id}")
                    self.__mysql.update(table="user_profiles", value="messages_weekly=messages_weekly+1",
                                        clause=f"WHERE id={author.id}")

                    self.__bot_instance.check_user_progress(author)

    @staticmethod
    def __get_valid_word_percentage(string, dictionaries=None):
        """
        Ermittelt den Prozentsatz, zu dem ein String aus tatsächlich existierenden Wörtern besteht, unter Verwendung
        einer oder mehrerer Wörterbücher.

        :param string: Der zu überprüfende String.
        :param dictionaries: Eine Liste von Wörterbüchern.
        :return: Der Prozentsatz, zu dem der String aus tatsächlich existierenden Wörtern besteht.
        """
        if dictionaries is None:
            # Wenn keine Wörterbücher angegeben sind, verwende alle verfügbaren Wörterbücher
            dictionaries = enchant.list_languages()

        # Erstelle eine Liste von Wörterbuch-Objekten
        dictionary_objects = [enchant.Dict(d) for d in dictionaries]

        # Entferne alle Satzzeichen und Zahlen aus dem String
        cleaned_string = re.sub(r'[^\w\s]', '', string)

        # Teile den String in Wörter auf
        words = cleaned_string.split()

        # Zähle, wie viele Wörter in den Wörterbüchern enthalten sind
        valid_word_count = sum(1 for word in words if any(d.check(word.lower()) for d in dictionary_objects))

        # Berechne den Prozentsatz der gültigen Wörter
        valid_word_percentage = valid_word_count / len(words) * 100

        # Gib den Prozentsatz zurück
        return valid_word_percentage
