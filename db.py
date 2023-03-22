import json
from datetime import datetime

from peewee import *

db = SqliteDatabase('edith.db')
# db = MySQLConnectorDatabase('edith', host='localhost', user='E.D.I.T.H', password='&fEvzV86)UMHt:J$')


class ModelBase(Model):
    class Meta:
        database = db


class Guild(ModelBase):
    class Setting(ModelBase):
        id = BigAutoField(primary_key=True)
        welcome_msg = CharField(null=True)
        leave_msg = CharField(null=True)
        msg_channel = BigIntegerField(null=True)
        log_category = BigIntegerField(null=True)
        messages_channel = BigIntegerField(null=True)
        logging_level = IntegerField(default=0)
        error_channel = BigIntegerField(null=True)
        default_role = BigIntegerField(null=True)

    id = BigIntegerField(primary_key=True)
    settings = ForeignKeyField(Setting, to_field="id")


class User(ModelBase):
    class DailyTask(ModelBase):
        id = BigAutoField(primary_key=True)
        description = TextField()
        accomplish_type = CharField()
        amount = IntegerField()
        xp = IntegerField()
        completed = BooleanField(default=False)
        acknowledged = BooleanField(default=False)

    class DailyProgress(ModelBase):
        id = BigAutoField(primary_key=True)
        time_in_voice = BigIntegerField(default=0)
        messages_send = BigIntegerField(default=0)
        movies_guessed = BigIntegerField(default=0)

    class WeeklyTask(ModelBase):
        id = BigAutoField(primary_key=True)
        description = TextField()
        accomplish_type = CharField()
        amount = IntegerField()
        xp = IntegerField()
        completed = BooleanField(default=False)
        acknowledged = BooleanField(default=False)

    class WeeklyProgress(ModelBase):
        id = BigAutoField(primary_key=True)
        time_in_voice = BigIntegerField(default=0)
        messages_send = BigIntegerField(default=0)
        movies_guessed = BigIntegerField(default=0)

    class Statistic(ModelBase):
        id = BigAutoField(primary_key=True)
        time_in_voice = BigIntegerField(default=0)
        messages_send = BigIntegerField(default=0)

    id = BigIntegerField(primary_key=True)
    xp = BigIntegerField(default=0)
    daily_tasks = ManyToManyField(DailyTask)
    daily_progress = ForeignKeyField(DailyProgress, to_field="id")
    weekly_tasks = ManyToManyField(WeeklyTask)
    weekly_progress = ForeignKeyField(WeeklyProgress, to_field="id")
    statistics = ForeignKeyField(Statistic, to_field="id")


UserDailyTasks = User.daily_tasks.get_through_model()
UserWeeklyTasks = User.weekly_tasks.get_through_model()


class Instance(ModelBase):
    id = BigIntegerField(primary_key=True)
    user = ForeignKeyField(User, to_field="id")
    channel_id = BigIntegerField()
    guild = ForeignKeyField(Guild, to_field="id")
    type = CharField()
    data = TextField(default="{}")


class PollVote(ModelBase):
    id = BigAutoField(primary_key=True)
    user = ForeignKeyField(User, to_field="id")
    poll_id = ForeignKeyField(Instance, to_field="id")
    answer_id = IntegerField()


class CustomChannel(ModelBase):
    id = BigIntegerField(primary_key=True)
    guild = ForeignKeyField(Guild, to_field="id")


class Backup(ModelBase):
    id = BigAutoField(primary_key=True)
    user = ForeignKeyField(User, to_field="id")
    guild = ForeignKeyField(Guild, to_field="id")
    data = TextField(default="{}")
    date = DateTimeField(default=datetime.now)


class SCMCreator(ModelBase):
    guild = ForeignKeyField(Guild, to_field="id")
    channel = ForeignKeyField(CustomChannel, to_field="id")


class SCMRoom(ModelBase):
    id = BigIntegerField(primary_key=True)
    guild = ForeignKeyField(Guild, to_field="id")
    channels = TextField(default="{}")
    user = ForeignKeyField(User, to_field="id")
    instance = ForeignKeyField(Instance, to_field="id")
    is_permanent = BooleanField(default=0)


class SCMUser(ModelBase):
    id = BigIntegerField(primary_key=True)
    user = ForeignKeyField(User, to_field="id")
    room = ForeignKeyField(SCMRoom, to_field="id")
    guild = ForeignKeyField(Guild, to_field="id")
    status = CharField()


class SCMRole(ModelBase):
    id = BigIntegerField(primary_key=True)
    guild = ForeignKeyField(Guild, to_field="id")
    emoji = CharField()


class SCMRoomRole(ModelBase):
    id = BigIntegerField(primary_key=True)
    role = ForeignKeyField(SCMRole, to_field="id")
    room = ForeignKeyField(SCMRoom, to_field="id")


class MovieGuess(ModelBase):
    id = BigAutoField(primary_key=True)
    user = ForeignKeyField(User, to_field="id")
    movie_id = CharField()
    num_clues = IntegerField()


class VoiceSession(ModelBase):
    user = ForeignKeyField(User, to_field="id", primary_key=True)
    guild = ForeignKeyField(Guild, to_field="id")
    start_time = DateTimeField(default=datetime.now)


class MusicSong(ModelBase):
    id = BigAutoField(primary_key=True)
    url = CharField(max_length=255, null=False)
    data = TextField(default="{}")
    is_playing = BooleanField(default=False)
    guild = ForeignKeyField(Guild, to_field="id")
    added_by = ForeignKeyField(User, to_field="id")
    added_at = DateTimeField(default=datetime.now)


class MusicInstance(ModelBase):
    guild = ForeignKeyField(Guild, to_field="id", primary_key=True)
    user = ForeignKeyField(User, to_field="id")
    channel_id = BigIntegerField(null=False)
    currently_playing = ForeignKeyField(MusicSong, to_field="id")


db.create_tables([Guild.Setting, Guild,
                  User.DailyTask, User.DailyProgress, User.WeeklyProgress, User.WeeklyTask, User.Statistic, User,
                  UserDailyTasks, UserWeeklyTasks,
                  Instance, PollVote, CustomChannel, Backup, SCMCreator, SCMRoom, SCMUser, SCMRole, SCMRoomRole,
                  MovieGuess, VoiceSession, MusicSong, MusicInstance])
