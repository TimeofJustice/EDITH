import nextcord

import db
import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, event: nextcord.ScheduledEvent):
        id = event.id

        birthday = db.Birthday.get_or_none(db.Birthday.event_id == id)

        if birthday is not None:
            birthday.delete_instance()
