import db
import dbLite
import dbMySql

# Get data from litesql and insert it into the new mysql database.

dbOld = dbMySql

# Setting
settings = dbOld.Guild.Setting.select()
for setting in settings:
    try:
        db.Guild.Setting.create(
            id=setting.id,
            welcome_msg=setting.welcome_msg,
            leave_msg=setting.leave_msg,
            msg_channel=setting.msg_channel,
            log_category=setting.log_category,
            messages_channel=setting.messages_channel,
            logging_level=setting.logging_level,
            error_channel=setting.error_channel,
            default_role=setting.default_role
        )
    except Exception as e:
        print(f"In 'Setting' ({setting.id}):\n{e}")

# Guild
guilds = dbOld.Guild.select()
for guild in guilds:
    try:
        db.Guild.create(
            id=guild.id,
            settings=guild.settings.id
        )
    except Exception as e:
        print(f"In 'Guild' ({guild.id}):\n{e}")

# DailyTask
dailyTasks = dbOld.User.DailyTask.select()
for dailyTask in dailyTasks:
    try:
        db.User.DailyTask.create(
            id=dailyTask.id,
            description=dailyTask.description,
            accomplish_type=dailyTask.accomplish_type,
            amount=dailyTask.amount,
            xp=dailyTask.xp,
            completed=dailyTask.completed,
            acknowledged=dailyTask.acknowledged
        )
    except Exception as e:
        print(f"In 'DailyTask' ({dailyTask.id}):\n{e}")

# DailyProgress
dailyProgresses = dbOld.User.DailyProgress.select()
for dailyProgress in dailyProgresses:
    try:
        db.User.DailyProgress.create(
            id=dailyProgress.id,
            time_in_voice=dailyProgress.time_in_voice,
            messages_send=dailyProgress.messages_send,
            movies_guessed=dailyProgress.movies_guessed
        )
    except Exception as e:
        print(f"In 'DailyProgress' ({dailyProgress.id}):\n{e}")

# WeeklyTask
weeklyTasks = dbOld.User.WeeklyTask.select()
for weeklyTask in weeklyTasks:
    try:
        db.User.WeeklyTask.create(
            id=weeklyTask.id,
            description=weeklyTask.description,
            accomplish_type=weeklyTask.accomplish_type,
            amount=weeklyTask.amount,
            xp=weeklyTask.xp,
            completed=weeklyTask.completed,
            acknowledged=weeklyTask.acknowledged
        )
    except Exception as e:
        print(f"In 'WeeklyTask' ({weeklyTask.id}):\n{e}")

# WeeklyProgress
weeklyProgresses = dbOld.User.WeeklyProgress.select()
for weeklyProgress in weeklyProgresses:
    try:
        db.User.WeeklyProgress.create(
            id=weeklyProgress.id,
            time_in_voice=weeklyProgress.time_in_voice,
            messages_send=weeklyProgress.messages_send,
            movies_guessed=weeklyProgress.movies_guessed
        )
    except Exception as e:
        print(f"In 'WeeklyProgress' ({weeklyProgress.id}):\n{e}")

# Statistics
statistics = dbOld.User.Statistic.select()
for statistic in statistics:
    try:
        db.User.Statistic.create(
            id=statistic.id,
            time_in_voice=statistic.time_in_voice,
            messages_send=statistic.messages_send
        )
    except Exception as e:
        print(f"In 'Statistic' ({statistic.id}):\n{e}")

# User
users = dbOld.User.select()
for user in users:
    try:
        db.User.create(
            id=user.id,
            xp=user.xp,
            daily_progress=user.daily_progress.id,
            weekly_progress=user.weekly_progress.id,
            statistics=user.statistics.id
        )

        newUser = db.User.get_or_none(db.User.id == user.id)

        newUser.daily_tasks.add([dailyTask.id for dailyTask in user.daily_tasks])
        newUser.weekly_tasks.add([weeklyTask.id for weeklyTask in user.weekly_tasks])

        newUser.save()
    except Exception as e:
        print(f"In 'User' ({user.id}):\n{e}")

# Instance
instances = dbOld.Instance.select()
for instance in instances:
    try:
        db.Instance.create(
            id=instance.id,
            user=instance.user.id,
            channel_id=instance.channel_id,
            guild=instance.guild.id,
            type=instance.type,
            data=instance.data
        )
    except Exception as e:
        print(f"In 'Instance' ({instance.id}):\n{e}")

# PollVote
pollVotes = dbOld.PollVote.select()
for pollVote in pollVotes:
    try:
        db.PollVote.create(
            id=pollVote.id,
            user=pollVote.user.id,
            poll_id=pollVote.poll_id,
            answer_id=pollVote.answer_id
        )
    except Exception as e:
        print(f"In 'PollVote' ({pollVote.id}):\n{e}")

# CustomChannel
customChannels = dbOld.CustomChannel.select()
for customChannel in customChannels:
    try:
        db.CustomChannel.create(
            id=customChannel.id,
            guild=customChannel.guild.id
        )
    except Exception as e:
        print(f"In 'CustomChannel' ({customChannel.id}):\n{e}")

# Backup
backups = dbOld.Backup.select()
for backup in backups:
    try:
        db.Backup.create(
            id=backup.id,
            user=backup.user.id,
            guild=backup.guild.id,
            data=backup.data,
            date=backup.date
        )
    except Exception as e:
        print(f"In 'Backup' ({backup.id}):\n{e}")

# SCMCreator
scmCreator = dbOld.SCMCreator.select()
for scm in scmCreator:
    try:
        db.SCMCreator.create(
            guild=scm.guild.id,
            channel=scm.channel.id
        )
    except Exception as e:
        print(f"In 'SCMCreator' ({scm.id}):\n{e}")

# SCMRoom
scmRooms = dbOld.SCMRoom.select()
for scmRoom in scmRooms:
    try:
        db.SCMRoom.create(
            id=scmRoom.id,
            guild=scmRoom.guild.id,
            channels=scmRoom.channels,
            user=scmRoom.user.id,
            instance=scmRoom.instance.id,
            is_permanent=scmRoom.is_permanent
        )
    except Exception as e:
        print(f"In 'SCMRoom' ({scmRoom.id}):\n{e}")

# SCMUser
scmUsers = dbOld.SCMUser.select()
for scmUser in scmUsers:
    try:
        db.SCMUser.create(
            id=scmUser.id,
            user=scmUser.user.id,
            room=scmUser.room.id,
            guild=scmUser.guild.id,
            status=scmUser.status
        )
    except Exception as e:
        print(f"In 'SCMUser' ({scmUser.id}):\n{e}")

# SCMRole
scmRoles = dbOld.SCMRole.select()
for scmRole in scmRoles:
    try:
        db.SCMRole.create(
            id=scmRole.id,
            guild=scmRole.guild.id,
            emoji=scmRole.emoji
        )
    except Exception as e:
        print(f"In 'SCMRole' ({scmRole.id}):\n{e}")

# SCMRoomRole
scmRoomRoles = dbOld.SCMRoomRole.select()
for scmRoomRole in scmRoomRoles:
    try:
        db.SCMRoomRole.create(
            id=scmRoomRole.id,
            role=scmRoomRole.role.id,
            room=scmRoomRole.room.id
        )
    except Exception as e:
        print(f"In 'SCMRoomRole' ({scmRoomRole.id}):\n{e}")

# MovieGuess
movieGuesses = dbOld.MovieGuess.select()
for movieGuess in movieGuesses:
    try:
        db.MovieGuess.create(
            id=movieGuess.id,
            user=movieGuess.user.id,
            movie_id=movieGuess.movie_id,
            num_clues=movieGuess.num_clues
        )
    except Exception as e:
        print(f"In 'MovieGuess' ({movieGuess.id}):\n{e}")

# VoiceSession
voiceSessions = dbOld.VoiceSession.select()
for voiceSession in voiceSessions:
    try:
        db.VoiceSession.create(
            user=voiceSession.user.id,
            guild=voiceSession.guild.id,
            start_time=voiceSession.start_time
        )
    except Exception as e:
        print(f"In 'VoiceSession' ({voiceSession.id}):\n{e}")

# MusicSong
musicSongs = dbOld.MusicSong.select()
for musicSong in musicSongs:
    try:
        db.MusicSong.create(
            id=musicSong.id,
            url=musicSong.url,
            data=musicSong.data,
            is_playing=musicSong.is_playing,
            guild=musicSong.guild.id,
            added_by=musicSong.added_by.id,
            added_at=musicSong.added_at
        )
    except Exception as e:
        print(f"In 'MusicSong' ({musicSong.id}):\n{e}")

# MusicInstance
musicInstances = dbOld.MusicInstance.select()
for musicInstance in musicInstances:
    try:
        db.MusicInstance.create(
            guild=musicInstance.guild.id,
            user=musicInstance.user.id,
            channel_id=musicInstance.channel_id,
            currently_playing=musicInstance.currently_playing.id
        )
    except Exception as e:
        print(f"In 'MusicInstance' ({musicInstance.id}):\n{e}")
