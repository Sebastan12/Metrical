import os
import time
import logging
from typing import Optional

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from prometheus_client import Counter, Gauge, Info, start_http_server

# ================== Config & setup ==================
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
PROM_PORT = int(os.getenv("PROM_PORT", "9108"))
TICK_SECONDS = float(os.getenv("TICK_SECONDS", "5"))

# Optional: library logs to a file
handler = logging.FileHandler(filename="../discord.log", encoding="utf-8", mode="w")

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
# Optional: nicer display names & reliable seeding of members on startup
# (Requires "Server Members Intent" enabled in the Dev Portal)
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================== Prometheus metrics ==================
# Counters (seconds, monotonic)
VOICE_USER_SECONDS = Counter(
    "voice_user_seconds_total",
    "Cumulative seconds a user spent in any voice channel",
    ["guild_id", "user_id"],
)
VOICE_CHANNEL_ACTIVE_SECONDS = Counter(
    "voice_channel_active_seconds_total",
    "Cumulative seconds a voice channel had >=1 user (union time)",
    ["guild_id", "channel_id", "channel_name"],
)
VOICE_GUILD_ACTIVE_SECONDS = Counter(
    "voice_guild_active_seconds_total",
    "Cumulative seconds a guild had >=1 user in any voice channel (union time)",
    ["guild_id", "guild_name"],
)

# Gauges (instantaneous)
VOICE_CHANNEL_ACTIVE = Gauge(
    "voice_channel_active",
    "1 if a voice channel has >=1 user, else 0",
    ["guild_id", "channel_id", "channel_name"],
)
VOICE_CHANNEL_ACTIVE_USERS = Gauge(
    "voice_channel_active_users",
    "Current number of users in the voice channel",
    ["guild_id", "channel_id", "channel_name"],
)

# "Info" metrics (IDs -> latest names for pretty dashboards)
DISCORD_USER = Info(
    "discord_user",
    "Latest known username/global_name for a user_id",
    ["user_id"],
)
DISCORD_USER_DISPLAY = Info(
    "discord_user_display",
    "Latest known display_name (nickname) for a user_id in a guild",
    ["guild_id", "user_id"],
)

# ================== In-memory presence state ==================
# (guild_id, user_id) -> {"channel_id": int}
active_users: dict[tuple[int, int], dict[str, int]] = {}

# (guild_id, channel_id) -> set(user_id)
channel_presence: dict[tuple[int, int], set[int]] = {}

# Monotonic clock for accurate elapsed time
_last_tick = time.monotonic()

# ================== Helpers ==================
def _labels_channel(guild: discord.Guild, channel_id: int):
    ch = guild.get_channel(channel_id)
    name = ch.name if isinstance(ch, discord.VoiceChannel) else f"id:{channel_id}"
    return {"guild_id": str(guild.id), "channel_id": str(channel_id), "channel_name": name}

def _labels_guild(guild: discord.Guild):
    return {"guild_id": str(guild.id), "guild_name": guild.name or f"id:{guild.id}"}

def _add_presence(gid: int, cid: Optional[int], uid: int) -> None:
    if cid is None:
        return
    key = (gid, cid)
    s = channel_presence.get(key)
    if s is None:
        s = set()
        channel_presence[key] = s
    s.add(uid)

def _remove_presence(gid: int, cid: Optional[int], uid: int) -> None:
    if cid is None:
        return
    key = (gid, cid)
    s = channel_presence.get(key)
    if s and uid in s:
        s.remove(uid)
        if not s:
            channel_presence.pop(key, None)

def _update_channel_gauges(guild: discord.Guild, channel_id: int) -> None:
    labels = _labels_channel(guild, channel_id)
    users = len(channel_presence.get((guild.id, channel_id), set()))
    VOICE_CHANNEL_ACTIVE_USERS.labels(**labels).set(users)
    VOICE_CHANNEL_ACTIVE.labels(**labels).set(1 if users > 0 else 0)

def _set_user_info(user: discord.abc.User) -> None:
    # Record the latest username & global_name for this user_id
    username = getattr(user, "name", None) or ""
    global_name = getattr(user, "global_name", None) or ""
    DISCORD_USER.labels(user_id=str(user.id)).info({
        "username": username,
        "global_name": global_name,
    })

def _set_member_display(member: discord.Member) -> None:
    # Record the latest display_name (guild nickname fallback to username/global_name)
    display_name = member.display_name or getattr(member, "global_name", None) or member.name
    DISCORD_USER_DISPLAY.labels(
        guild_id=str(member.guild.id),
        user_id=str(member.id),
    ).info({"display_name": display_name})

# ================== Events ==================
@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")
    for g in bot.guilds:
        print(f" - connected to: {g.name} (gid={g.id})")

    # Start Prometheus exporter & accrual loop
    start_http_server(PROM_PORT)
    print(f"[metrics] Prometheus exporter on :{PROM_PORT}/metrics")
    if not accrue_loop.is_running():
        accrue_loop.start()

    # Seed current voice state so people already in voice are counted immediately
    await seed_current_voice_state()

async def seed_current_voice_state():
    """Populate presence from current voice channels once on startup."""
    seeded_users = 0
    for guild in bot.guilds:
        for ch in getattr(guild, "voice_channels", []):
            for m in ch.members:
                gid, uid = guild.id, m.id
                active_users[(gid, uid)] = {"channel_id": ch.id}
                _add_presence(gid, ch.id, uid)
                _update_channel_gauges(guild, ch.id)
                # also set latest names
                _set_user_info(m)
                _set_member_display(m)
                seeded_users += 1
    if seeded_users:
        print(f"[seed] Initialized presence for {seeded_users} member(s) already in voice.")

# ---- JOIN / LEAVE console prints + presence updates ----
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    uid = member.id
    gid = member.guild.id
    name = member.display_name or getattr(member, "global_name", None) or member.name

    # JOIN
    if not before.channel and after.channel:
        active_users[(gid, uid)] = {"channel_id": after.channel.id}
        _add_presence(gid, after.channel.id, uid)
        print(f"[JOIN] {name} (uid={uid}) joined #{after.channel.name} | guild={member.guild.name} (gid={gid})")
        _update_channel_gauges(member.guild, after.channel.id)
        # refresh name info
        _set_user_info(member)
        _set_member_display(member)
        return

    # LEAVE
    if before.channel and not after.channel:
        _remove_presence(gid, before.channel.id, uid)
        active_users.pop((gid, uid), None)
        print(f"[LEAVE] {name} (uid={uid}) left #{before.channel.name} | guild={member.guild.name} (gid={gid})")
        _update_channel_gauges(member.guild, before.channel.id)
        # still update name info (no harm)
        _set_user_info(member)
        _set_member_display(member)
        return

    # MOVE (optional: keep prints minimal; gauges/state still updated)
    if before.channel and after.channel and before.channel.id != after.channel.id:
        active_users.setdefault((gid, uid), {})["channel_id"] = after.channel.id
        _remove_presence(gid, before.channel.id, uid)
        _add_presence(gid, after.channel.id, uid)
        _update_channel_gauges(member.guild, before.channel.id)
        _update_channel_gauges(member.guild, after.channel.id)
        # refresh name info
        _set_user_info(member)
        _set_member_display(member)

# ---- Name change events (keep "info" metrics current) ----
@bot.event
async def on_user_update(before: discord.User, after: discord.User):
    _set_user_info(after)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    _set_member_display(after)

# ================== Accrual loop (monotonic) ==================
@tasks.loop(seconds=TICK_SECONDS)
async def accrue_loop():
    """Increment counters every TICK_SECONDS based on current presence."""
    global _last_tick
    now_mono = time.monotonic()
    dt = now_mono - _last_tick
    if dt <= 0:
        return
    _last_tick = now_mono

    guild_map = {g.id: g for g in bot.guilds}

    # 1) Per-user totals
    for (gid, uid), _info in list(active_users.items()):
        VOICE_USER_SECONDS.labels(guild_id=str(gid), user_id=str(uid)).inc(dt)

    # 2) Per-channel union + live gauges
    active_guilds: set[int] = set()
    for (gid, cid), users in list(channel_presence.items()):
        guild = guild_map.get(gid)
        if guild is None:
            continue
        labels = _labels_channel(guild, cid)
        if users:
            VOICE_CHANNEL_ACTIVE_SECONDS.labels(**labels).inc(dt)
            VOICE_CHANNEL_ACTIVE.labels(**labels).set(1)
            VOICE_CHANNEL_ACTIVE_USERS.labels(**labels).set(len(users))
            active_guilds.add(gid)
        else:
            VOICE_CHANNEL_ACTIVE.labels(**labels).set(0)
            VOICE_CHANNEL_ACTIVE_USERS.labels(**labels).set(0)

    # 3) Per-guild union time
    for g in bot.guilds:
        if g.id in active_guilds:
            VOICE_GUILD_ACTIVE_SECONDS.labels(**_labels_guild(g)).inc(dt)

# ================== Run ==================
if not token:
    raise SystemExit("Set DISCORD_TOKEN in your environment (e.g., in .env).")

bot.run(token, log_handler=handler, log_level=logging.INFO)
