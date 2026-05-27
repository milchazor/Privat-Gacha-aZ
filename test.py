import asyncio
import io
import sys
import json
import datetime
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
import discord
import mss

with open("json_files/settings.json", "r") as f:
    _settings = json.load(f)

API_KEY = _settings["discord_api_key"]
CHANNEL_ID = int(_settings["log_status_channel"])

# mock all modules with game-level code before importing stations
_screen_mock = MagicMock()
_screen_mock.screen_resolution = 1440

_settings_mock = MagicMock()
for k, v in _settings.items():
    setattr(_settings_mock, k, v)

for _mod in [
    "settings",
    "source.utility.screen",
    "source.utility.local_player",
    "source.utility.windows",
    "source.utility.utils",
    "source.utility.template",
    "source.utility.variables",
    "source.ASA.strucutres.teleporter",
    "source.ASA.strucutres.inventory",
    "source.ASA.strucutres.bed",
    "source.ASA.stations.custom_stations",
    "source.ASA.player.player_inventory",
    "source.ASA.player.player_state",
    "source.ASA.player.console",
    "source.ASA.player.tribelog",
    "source.gacha_bot.config",
    "source.gacha_bot.render",
    "source.gacha_bot.deposit",
    "source.gacha_bot.gacha",
    "source.gacha_bot.iguanadon",
    "source.gacha_bot.pego",
    "source.join_sim.source.main",
    "source.join_sim.source.utility.screen",
    "source.logs.gachalogs",
]:
    sys.modules[_mod] = MagicMock()

sys.modules["settings"] = _settings_mock
sys.modules["source.utility.screen"] = _screen_mock

import source.gacha_bot.stations as stations

def take_screenshot():
    with mss.mss() as sct:
        region = {"top": 0, "left": 0, "width": 800, "height": 600}
        frame = sct.grab(region)
        return np.array(frame)

def count_red_pixels(img):
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    red_mask = (r > 150) & (r > b * 2) & (r > g * 2)
    return int(np.sum(red_mask))

async def fetch_old_screenshot(channel):
    async for message in channel.history(limit=20):
        if message.attachments:
            data = await message.attachments[0].read()
            arr = np.frombuffer(data, dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return None

async def test_checklogs_sends_image():
    captured = {}

    def mock_get_screen_roi(x, y, w, h):
        img = take_screenshot()
        captured["img"] = img
        return img

    with patch("source.gacha_bot.stations.player_state.check_state"), \
         patch("source.gacha_bot.stations.tribelog.open"), \
         patch("source.gacha_bot.stations.variables.get_pixel_loc", return_value=0), \
         patch("source.gacha_bot.stations.screen.get_screen_roi", side_effect=mock_get_screen_roi), \
         patch("source.gacha_bot.stations.logs.tribe_logger"):
        task = stations.checklogs(name="test", delay=300)
        task.execute()

    new_img = captured["img"]
    _, buf = cv2.imencode(".png", new_img)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(CHANNEL_ID)
        if channel is None:
            print(f"ERROR: channel {CHANNEL_ID} not found - check log_status_channel in settings.json")
            await client.close()
            return

        old_img = await fetch_old_screenshot(channel)
        red_alert = False
        if old_img is not None:
            old_red = count_red_pixels(old_img)
            new_red = count_red_pixels(new_img)
            print(f"red pixels — old: {old_red}, new: {new_red}")
            if old_red > 0 and new_red > old_red * 1.05:
                red_alert = True

        await channel.purge()
        file = discord.File(io.BytesIO(buf.tobytes()), filename="tribe_log.png")
        await channel.send(f"tribe log screenshot taken at: {timestamp}", file=file)
        if red_alert:
            await channel.send("HOUSE UNDER SIEGE ?! @here")
            print("@here sent")
        print("image sent successfully")
        await client.close()

    await client.start(API_KEY)

if __name__ == "__main__":
    asyncio.run(test_checklogs_sends_image())
