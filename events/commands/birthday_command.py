import datetime

import nextcord

import db
from events import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        super().__init__(interaction, bot_instance, data)

    async def run(self):
        if self.__data['subcommand'] == 'add':
            name = self.__data['name']
            date = self.__data['date']

            birthDate = datetime.datetime.strptime(date, "%d.%m.%Y")
            eventDate = birthDate.replace(year=datetime.datetime.now().year)

            if eventDate < datetime.datetime.now():
                eventDate = eventDate.replace(year=datetime.datetime.now().year + 1)

            birthdayEntry = db.Birthday.create(
                user=name,
                date=birthDate
            )

            event = await self.__guild.create_scheduled_event(
                name=f"{name}'s Geburtstag",
                description=f"{name} was born on {birthDate.strftime('%d.%m.%Y')}.",
                start_time=eventDate,
                end_time=eventDate + datetime.timedelta(days=1),
                entity_type=nextcord.ScheduledEventEntityType.external,
                metadata=nextcord.EntityMetadata(location="ㅤ")
            )

            birthdayEntry.event_id = event.id
            birthdayEntry.save()

            await self.__interaction.send(embed=nextcord.Embed(
                title=f"{name}'s Birthday",
                description=f"{name}'s birthday was added successfully!",
                color=nextcord.Color.random()
            ), ephemeral=True)
        elif self.__data['subcommand'] == 'reload':
            birthdays = db.Birthday.select()

            message = await self.__interaction.send(embed=nextcord.Embed(
                title="Birthday",
                description=f"All birthdays are being reloaded. (0/{len(birthdays)})",
                color=nextcord.Color.random()
            ), ephemeral=True)

            current = 0

            for birthday in birthdays:
                current += 1

                event = self.__guild.get_scheduled_event(birthday.event_id)

                if event is None or event.start_time.date() < datetime.date.today():
                    birthDate = birthday.date
                    eventDate = birthDate.replace(year=datetime.datetime.now().year)

                    if eventDate < datetime.date.today():
                        eventDate = eventDate.replace(year=datetime.datetime.now().year + 1)

                    event = await self.__guild.create_scheduled_event(
                        name=f"{birthday.user}'s Birthday",
                        description=f"{birthday.user} was born on {birthDate.strftime('%d.%m.%Y')}.",
                        start_time=eventDate,
                        end_time=eventDate + datetime.timedelta(days=1),
                        entity_type=nextcord.ScheduledEventEntityType.external,
                        metadata=nextcord.EntityMetadata(location="ㅤ")
                    )

                    birthday.event_id = event.id
                    birthday.save()

                await message.edit(embed=nextcord.Embed(
                    title="Birthday",
                    description=f"All birthdays are being reloaded. ({current}/{len(birthdays)})",
                    color=nextcord.Color.random()
                ))
