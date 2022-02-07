import asyncio
import urllib.request
import configparser

from mopidy_asyncio_client import MopidyClient
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

class PirateDisplay():
    def __init__(self):
        self.SPI_SPEED_MHZ = 80

        self.st7789 = ST7789(
                rotation=90,
                port=0,
                cs=1,
                dc=9,
                backlight=13,
                spi_speed_hz=self.SPI_SPEED_MHZ * 1000 * 1000
        )

        config = configparser.ConfigParser()
        config.read("config.ini")

        self.mopidy_host = config["pirate-display"]["mopidy_host"]
        self.mopidy_web_port = config["pirate-display"]["mopidy_web_port"]

    async def connect(self):
        async with MopidyClient(host=self.mopidy_host) as mopidy:
            self.running_client = mopidy
            mopidy.bind('track_playback_started', self.playback_started_handler)
            await self.display(mopidy)

            while True:
                await asyncio.sleep(1)


    async def playback_started_handler(self, data):
        """Updates the diplay when the track changes"""
        await self.display(self.running_client)


    async def display(self, client):
        current_track = await client.playback.get_current_tl_track()

        image_uri = current_track["track"]["album"]["uri"]
        image_location = await client.library.get_images([image_uri])

        image_url = f"http://{self.mopidy_host}:{self.mopidy_web_port}{image_location[image_uri][0]['uri']}"
        urllib.request.urlretrieve(image_url, "/tmp/album.jpeg")

        image = Image.open("/tmp/album.jpeg")
        image = image.resize((240,240))
        font = ImageFont.truetype("/usr/local/lib/python3.9/dist-packages/font_roboto/files/Roboto-Black.ttf", 20)
        draw = ImageDraw.Draw(image)
        draw.multiline_text((10,10), align="left", text=current_track["track"]["name"], font=font, stroke_fill=(0,0,255), stroke_width=2)

        image.show()
        self.st7789.display(image)


if __name__ == '__main__':
    pirate_display = PirateDisplay()
    asyncio.run(pirate_display.connect())
