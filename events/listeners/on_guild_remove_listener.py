import nextcord

import db
import events.listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, guild: nextcord.Guild):
        guild = db.Guild.get_or_none(db.Guild.id == guild.id)

        db.CustomChannel.delete().where(db.CustomChannel.guild == guild).execute()
        db.Instance.delete().where(db.Instance.guild == guild).execute()
        db.SCMCreator.delete().where(db.SCMCreator.guild == guild).execute()
        db.SCMRole.delete().where(db.SCMRole.guild == guild).execute()
        rooms = db.SCMRoom.select().where(db.SCMRoom.guild == guild).execute()
        db.SCMRoom.delete().where(db.SCMRoom.guild == guild).execute()

        for room in rooms:
            db.SCMRoomRole.delete().where(db.SCMRoomRole.room == room).execute()

        db.SCMUser.delete().where(db.SCMUser.guild == guild).execute()
        guild.delete_instance()
        guild.settings.delete_instance()
