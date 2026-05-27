import discord
import json 
from discord import app_commands
from discord.ext import commands
import asyncio
import time 
import settings 
from source.logs import discordbot,botoptions
import task_manager
import source.gacha_bot.stations as stations
import source.ASA.player.player_inventory as inventory
from source.utility.colour_checks import console_output, output_oranage_tp_pixel

class discord_commands(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.running_task = []
        self.start_time = 0

    async def send_new_logs(self):
        log_channel = self.bot.get_channel(int(settings.log_channel_gacha))
        last_position = 0
        
        while True:
            with open("source/logs/logs.txt", 'r') as file:
                file.seek(last_position)
                new_logs = file.read()
                if new_logs:
                    if len(new_logs) >= 1999:
                        await log_channel.send(f"New logs:\n```log limit reached 2000 skipping```")
                    else:
                        await log_channel.send(f"New logs:\n```{new_logs}```")
                    last_position = file.tell()
            await asyncio.sleep(5)

    async def send_tribe_logs(self):
        log_channel = self.bot.get_channel(int(settings.log_status_channel))
        last_position = 0
        while True:
            with open("source/logs/tribe_logs.txt", 'r') as file:
                file.seek(last_position)
                new_logs = file.read()
                if new_logs:
                    if len(new_logs) >= 1999:
                        await log_channel.send(f"New logs:\n```log limit reached 2000 skipping```")
                    else:
                        await log_channel.send(f"New logs:\n```{new_logs}```")
                    last_position = file.tell()
            await asyncio.sleep(5)

    async def embed_send(self,queue_type):
        log_channel = 0
        if queue_type == "active_queue":
            log_channel = self.bot.get_channel(int(settings.log_active_queue))
        else:
            log_channel = self.bot.get_channel(int(settings.log_wait_queue))
        while True:
            embed_msg = await discordbot.embed_create(queue_type)
            await log_channel.purge()
            await log_channel.send(embed = embed_msg)
            await asyncio.sleep(30)
    
    @app_commands.command(name="pause", description="pauses the bot after the current task finishes")
    async def reset(self, interaction: discord.Interaction):
        stations.paused = True
        await interaction.response.send_message("bot will pause after the current task finishes. Use /continue to resume.")

    @app_commands.command(name="continue", description="resumes the bot after a /pause")
    async def resume(self, interaction: discord.Interaction):
        if stations.paused:
            stations.paused = False
            await interaction.response.send_message("bot resumed")
        else:
            await interaction.response.send_message("bot is not currently paused")


    @app_commands.command()
    async def start(self,interaction: discord.Interaction):
        self.start_time = time.time()
        logchn = self.bot.get_channel(int(settings.log_channel_gacha))
        if logchn:
            await logchn.send(f'bot starting up now')
        
        # resetting log files
        with open("source/logs/logs.txt", 'w') as file:
            file.write(f"")
        self.bot.loop.create_task(self.send_new_logs())
        
        
        await interaction.response.send_message(f"starting up bot now you have 5 seconds before start")
        time.sleep(5)
        asyncio.create_task(botoptions.task_manager_start())
        while task_manager.started == False:
            await asyncio.sleep(1)
        self.bot.loop.create_task(self.embed_send("active_queue"))
        self.bot.loop.create_task(self.embed_send("waiting_queue"))
        self.bot.loop.create_task(self.send_tribe_logs())
    
    async def get_time_diffrence(self,inital):
        time_difference = time.time() - inital
        days = time_difference / 86400
        hours = time_difference / 3600
        minutes = time_difference / 60
        seconds = time_difference

        if days >= 1:
            return f"{round(days,2)} days"
        else:
            return f"{round(hours,2)} hours"

    @app_commands.command(name="info",description="sends analytics for the bot")
    async def info(self,interaction: discord.Integration):
        if self.start_time == 0:
            await interaction.response.send_message("bot hasnt started up yet")
        else:
            await interaction.response.send_message(f"time since start: {await self.get_time_diffrence(self.start_time)} resets : {inventory.resets}")

    @app_commands.command(name="colour_checks",description="outputs pixel values ")
    async def colour_checks(self,interaction: discord.Interaction):
        await interaction.response.send_message(f"console mean output { console_output.output_mean_colour()} orange pixel {  output_oranage_tp_pixel.get_orange_pixel()}")

async def setup(bot):
    await bot.add_cog(discord_commands(bot))