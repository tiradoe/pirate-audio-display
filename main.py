import asyncio
import textwrap
from asyncio.tasks import create_task
import urllib.request
import configparser
import RPi.GPIO as GPIO

from mopidy_asyncio_client import MopidyClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
        self.buttons = [5,6,16,24]

        config = configparser.ConfigParser()
        config.read("config.ini")

        self.mopidy_host = config["pirate-display"]["mopidy_host"]
        self.mopidy_web_port = config["pirate-display"]["mopidy_web_port"]


    async def connect(self):
        """Create a connection to Mopidy"""
        await self.setup_buttons()
        self.loop = asyncio.get_running_loop()

        async with MopidyClient(host=self.mopidy_host) as mopidy:
            self.running_client = mopidy
            mopidy.bind('track_playback_started', self.playback_started_handler)
            await self.display(mopidy)

            while True:
                await asyncio.sleep(1)


    async def setup_buttons(self):
        """Add handlers to each button"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(5, GPIO.FALLING, self.handle_A, bouncetime=100)
        GPIO.add_event_detect(6, GPIO.FALLING, self.handle_B, bouncetime=100)
        GPIO.add_event_detect(16, GPIO.FALLING,self.handle_X, bouncetime=100)
        GPIO.add_event_detect(24, GPIO.FALLING, self.handle_Y, bouncetime=100)


    def handle_A(self,pin):
        """Decrease volume"""
        self.loop.create_task(self.update_volume('down'))


    def handle_B(self, pin):
        """Go to previous track"""
        self.loop.create_task(self.running_client.playback.previous())


    def handle_X(self,pin):
        """Increase Volume"""
        self.loop.create_task(self.update_volume('up'))


    def handle_Y(self, pin):
        """Play next track"""
        self.loop.create_task(self.running_client.playback.next())


    async def update_volume(self, direction):
        """Increase or decrease the Mopidy server volume"""
        current_volume = await self.loop.create_task(self.running_client.mixer.get_volume())
        if direction == 'up':
            await self.running_client.mixer.set_volume(current_volume + 15)
        else:
            await self.running_client.mixer.set_volume(current_volume - 15)


    async def playback_started_handler(self, data):
        """Update the diplay when the track changes"""
        await self.display(self.running_client)


    async def display(self, client):
        """Generate the image to be displayed and send it to the device screen"""
        current_track = await client.playback.get_current_tl_track()

        album_uri = current_track["track"]["album"]["uri"]
        album_art = await client.library.get_images([album_uri])

        # Use a black background if image isn't found
        try:
            image_url = f"http://{self.mopidy_host}:{self.mopidy_web_port}{album_art[album_uri][0]['uri']}"

            urllib.request.urlretrieve(image_url, "/tmp/album.jpeg")
            image = Image.open("/tmp/album.jpeg")
            image = image.filter(ImageFilter.GaussianBlur(5))
            image = image.resize((240,240))
        except:
            image = Image.new("RGB", (240, 240), (0,0,0))

        font = ImageFont.truetype("./fonts/Narifah-EaBWz.otf", 20)
        draw = ImageDraw.Draw(image)

        # Track name
        song_title = textwrap.wrap(current_track["track"]["name"], 20)
        draw.multiline_text((10,20), align="left", text= "\n".join(song_title), font=font, stroke_fill=(1,103,181), stroke_width=2)

        # Artist name
        artist = textwrap.wrap(current_track["track"]["artists"][0]["name"], 20)
        draw.multiline_text((10,190), align="left", text="\n".join(artist), font=font, stroke_fill=(1,103,181), stroke_width=2)

        image.show()

        self.st7789.display(image)


if __name__ == '__main__':
    pirate_display = PirateDisplay()
    try:
        asyncio.run(pirate_display.connect())
    except KeyboardInterrupt:
        pirate_display.loop.stop()
        print("Disconnected")
