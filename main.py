import discord
from discord.ext import commands

import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

# ---- JOIN / LEAVE console prints only ----
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    uid = member.id
    gid = member.guild.id
    # best-effort display name (no caching)
    name = member.display_name or getattr(member, "global_name", None) or member.name

    # JOIN
    if not before.channel and after.channel:
        print(f"[JOIN] {name} (uid={uid}) joined #{after.channel.name} | guild={member.guild.name} (gid={gid})")
        return

    # LEAVE
    if before.channel and not after.channel:
        print(f"[LEAVE] {name} (uid={uid}) left #{before.channel.name} | guild={member.guild.name} (gid={gid})")
        return

bot.run(token, log_handler=handler, log_level=logging.DEBUG)