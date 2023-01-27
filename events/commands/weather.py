import configparser
import json
import urllib.request
from datetime import datetime

import nextcord

import command


class Command(command.Command):
    def __init__(self, interaction: nextcord.Interaction, bot_instance, data=None):
        if data is None:
            data = {}

        super().__init__(interaction, bot_instance, data)

    async def run(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        api_key = config["DEFAULT"]["weather_api"]

        url = (f"http://api.openweathermap.org/data/2.5/weather"
               f"?q={self.__data['city']}&units=metric"
               f"&lang=en&APPID={api_key}").replace(" ", "%20")

        try:
            data = json.loads(urllib.request.urlopen(url).read())
        except Exception as e:
            embed = nextcord.Embed(
                color=nextcord.Colour.red(),
                description=f"It is to stormy outside to tell you the weather"
            )
            await self.__interaction.send(embed=embed, ephemeral=True)

            return e

        degree = data["wind"]["deg"]

        if 0 <= degree < 90:
            degree = f"north"
        elif 90 <= degree < 180:
            degree = f"east"
        elif 180 <= degree < 270:
            degree = f"south"
        elif 270 <= degree < 360:
            degree = f"west"
        else:
            degree = f"unknown"

        embed = nextcord.Embed(title=f"{data['weather'][0]['description'].capitalize()} "
                                     f"with {round(data['main']['temp'])}°C")
        embed.set_author(
            name=f"Weather in {data['name']}",
            icon_url="https://www.wetter.net//components/com_weather/assets/icons/0/250/6.png"
        )
        embed.add_field(
            name=f"Temperature",
            value=f"{round(data['main']['temp_min'])}°C - {round(data['main']['temp_max'])}°C\n"
                  f"Feels like {round(data['main']['feels_like'])}°C",
            inline=True
        )
        embed.add_field(
            name="Air-Quality",
            value=f"Humidity: {data['main']['humidity']}%\n"
                  f"Pressure: {round(data['main']['pressure'], 2)}hPa",
            inline=True
        )
        embed.add_field(
            name="Clouds and Wind",
            value=f"Cloudiness: {data['clouds']['all']}%\n"
                  f"With gusts up to {data['wind']['speed']}m/s from {degree}",
            inline=False
        )
        embed.add_field(
            name="Suntime",
            value=f"{datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')} - "
                  f"{datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')} MESZ",
            inline=True
        )

        await self.__interaction.send(embed=embed, ephemeral=True)
