import _thread
from datetime import datetime
import schedule
import nextcord

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
            self.__mysql.delete(table="voice_sessions", clause=f"WHERE member_id={member.id} and guild_id={guild.id}")

        if (is_joined or going_un_mute or is_moved) and not member.bot and not after.afk and not is_muted:
            self.__mysql.delete(table="voice_sessions", clause=f"WHERE member_id={member.id}")

            self.__mysql.insert(table="voice_sessions", colms="(member_id, start, guild_id)",
                                values=(member.id, datetime.now(), guild.id))

            self.init_worker_thread(member, guild)

    def init_worker_thread(self, member: nextcord.Member, guild: nextcord.Guild):
        _thread.start_new_thread(self.__start_worker, (self.__bot_instance, member, guild))

    def __start_worker(self, bot_instance, member: nextcord.Member, guild: nextcord.Guild):
        schedule.every().minute.do(self.__voice_worker, bot_instance=bot_instance, member=member, guild=guild)

    def __voice_worker(self, bot_instance, member: nextcord.Member, guild: nextcord.Guild):
        voice_session = self.__mysql.select(table="voice_sessions", colms="member_id, start",
                                            clause=f"WHERE member_id={member.id} and guild_id={guild.id}")

        if 0 < len(voice_session):
            session = voice_session[0]

            if member.voice is None:
                self.__mysql.delete(table="voice_sessions", clause=f"WHERE member_id={member.id}")
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
                self.__mysql.update(table="user_profiles", value="time_in_voice=time_in_voice+1",
                                    clause=f"WHERE id={member.id}")
                self.__mysql.update(table="user_profiles", value="voice_daily=voice_daily+1",
                                    clause=f"WHERE id={member.id}")
                self.__mysql.update(table="user_profiles", value="voice_weekly=voice_weekly+1",
                                    clause=f"WHERE id={member.id}")

                bot_instance.check_user_progress(member)
        else:
            return schedule.CancelJob
