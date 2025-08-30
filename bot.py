import discord
from discord.ext import commands, tasks
import asyncio
import time
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL_ID = 1403610637313245304
WATCH_CHANNEL_ID = 1390699163137605773
LOG_CHANNEL_ID_2 = 1404888102140510382

warnings = {}
spam_tracker = {}
MAX_MSG = 10
TIME_LIMIT = 10

OWNER_IDS = [
    826753238392111106,
    1307384491752554517,
    1169202696146911287,
    1181659154658631710
]

def is_owner(ctx):
    return ctx.author.id in OWNER_IDS

@tasks.loop(seconds=5)
async def change_status():
    statuses = [
        discord.Game("Nézi: By KEPY"),
        discord.Game("Nézi: dsc.gg/kepyyt")
    ]
    current = change_status.current_index
    await bot.change_presence(activity=statuses[current])
    change_status.current_index = (current + 1) % len(statuses)

change_status.current_index = 0

@bot.event
async def on_ready():
    print(f'✅ Bejelentkezve mint {bot.user}')
    change_status.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    now = time.time()

    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    spam_tracker[user_id].append(now)
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t <= TIME_LIMIT]

    if len(spam_tracker[user_id]) > MAX_MSG:
        role = discord.utils.get(message.guild.roles, name="Muted")
        if not role:
            role = await message.guild.create_role(name="Muted")
            for channel in message.guild.channels:
                await channel.set_permissions(role, speak=False, send_messages=False)

        await message.author.add_roles(role)
        await message.channel.send(f"🔇 {message.author.mention} automatikusan lenémítva spam miatt!")

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"⚠️ **Automata mute (SPAM miatt)**\n"
                f"**Felhasználó:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Csatorna:** {message.channel.mention}\n"
                f"**Időtartam:** VÉGTELEN (feloldás: `!unmute @felhasználó`)"
            )
        return

    if message.channel.id == WATCH_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID_2)
        if log_channel:
            await log_channel.send(f"{message.author.mention} írta: {message.content}")

    if "discord.gg/" in message.content and not is_owner(await bot.get_context(message)):
        await message.delete()
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"🚫 **Discord meghívó link törölve!**\n"
                f"**Felhasználó:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Csatorna:** {message.channel.mention}\n"
                f"**Tartalom:** {message.content}"
            )
        return

    await bot.process_commands(message)

# Moderátor parancsok
@bot.command()
@commands.check(is_owner)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} ki lett tiltva.")

# ... ide jöhet minden többi parancs ugyanúgy

# Bot token környezeti változóból
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
