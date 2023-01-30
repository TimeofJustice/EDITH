from mysql_bridge import Mysql


class Listener:
    def __init__(self, bot_instance, data=None):
        self.__mysql = Mysql()
        self.__bot_instance = bot_instance
        self.__bot = self.__bot_instance.get_bot()
        self.__data = data
