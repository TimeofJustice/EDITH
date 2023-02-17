import nextcord

import events.listener
from events.listeners import scm_listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(bot_instance, data)

    async def call(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        listener = scm_listener.Listener(self.__bot_instance)
        await listener.call(member, before, after)
