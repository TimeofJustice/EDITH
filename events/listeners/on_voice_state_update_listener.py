import _thread
import schedule
import nextcord

import db
import events.listener
from events.listeners import scm_listener


class Listener(events.listener.Listener):
    def __init__(self, bot_instance, data=None):
        super().__init__(bot_instance, data)

    async def call(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        listener = scm_listener.Listener(self.__bot_instance)
        await listener.call(member, before, after)

        guild = member.guild

        is_joined = before.channel is None and after.channel is not None
        is_left = before.channel is not None and after.channel is None
        is_moved = before.channel is not None and after.channel is not None
        going_mute = (not before.self_mute and after.self_mute) or (not before.mute and after.mute) or (
                not before.deaf and after.deaf)
        going_un_mute = (before.self_mute and not after.self_mute) or (before.mute and not after.mute) or (
                before.deaf and not after.deaf)
        is_muted = after.mute or after.deaf or after.self_mute or after.self_deaf

        if (is_left or going_mute or after.afk) and not member.bot:
            db.VoiceSession.delete().where(db.VoiceSession.user == member.id,
                                           db.VoiceSession.guild == guild.id).execute()

        if (is_joined or going_un_mute or is_moved) and not member.bot and not after.afk and not is_muted:
            db.VoiceSession.delete().where(db.VoiceSession.user == member.id).execute()

            user_data = db.User.get_or_none(id=member.id)
            guild_data = db.Guild.get_or_none(id=guild.id)

            db.VoiceSession.create(user=user_data, guild=guild_data)

            self.init_worker_thread(member, guild)

    def init_worker_thread(self, member: nextcord.Member, guild: nextcord.Guild):
        _thread.start_new_thread(self.__start_worker, (self.__bot_instance, member, guild))

    def __start_worker(self, bot_instance, member: nextcord.Member, guild: nextcord.Guild):
        schedule.every().minute.do(self.__voice_worker, bot_instance=bot_instance, member=member, guild=guild)

    def __voice_worker(self, bot_instance, member: nextcord.Member, guild: nextcord.Guild):
        voice_session = db.VoiceSession.get_or_none(user=member.id)
        user_data = db.User.get_or_none(id=member.id)

        if voice_session:
            if member.voice is None:
                db.VoiceSession.delete().where(db.VoiceSession.user == member.id).execute()
                return schedule.CancelJob
            else:
                voice_channel = member.voice.channel

            members_in_voice = voice_channel.members
            unique_members = []
            for member_in_voice in members_in_voice:
                if not (member_in_voice.bot or member_in_voice.voice.mute or member_in_voice.voice.deaf or
                        member_in_voice.voice.self_mute or member_in_voice.voice.self_deaf):
                    unique_members.append(member_in_voice)

            if 1 < len(unique_members):
                user_data.statistics.time_in_voice += 1
                user_data.daily_progress.time_in_voice += 1
                user_data.weekly_progress.time_in_voice += 1

                user_data.statistics.save()
                user_data.daily_progress.save()
                user_data.weekly_progress.save()

                bot_instance.check_user_progress(member)
        else:
            return schedule.CancelJob
