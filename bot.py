import discord
from discord.ext import commands, tasks
import asyncio
import time
import os
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# A csatorna, ahová a törölt link jelentése kerül
LOG_CHANNEL_ID = 1403610637313245304

# Csatorna, amit figyelünk az üzenetekre
WATCH_CHANNEL_ID = 1390699163137605773
# Csatorna, ahová az átírt üzenetek mennek
LOG_CHANNEL_ID_2 = 1404888102140510382

# Figyelmeztetések tárolása (felhasználó ID -> lista)
warnings = {}

# Spam figyeléshez
spam_tracker = {}
MAX_MSG = 10
TIME_LIMIT = 10

# Globális ownerek
OWNER_IDS = [
    826753238392111106,
    1209955933170438207,
    1042190618979483759,
    1119340107900653598
]

# Jogosultságkezelés
def is_owner(ctx):
    return ctx.author.id in OWNER_IDS

# Állapotváltó
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

    # Spam figyelés
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

    # Eredeti log
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

@bot.command()
@commands.check(is_owner)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} ki lett rúgva.")

@bot.command()
@commands.check(is_owner)
async def mute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, speak=False, send_messages=False)

    await member.add_roles(role)
    await ctx.send(f"🔇 {member.mention} le lett némítva.")

@bot.command()
@commands.check(is_owner)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"🔊 {member.mention} némítása fel lett oldva.")
    else:
        await ctx.send(f"{member.mention} nincs lenémítva.")

@bot.command()
@commands.check(is_owner)
async def warn(ctx, member: discord.Member, *, reason: str = "Nincs megadva ok"):
    user_id = member.id
    if user_id not in warnings:
        warnings[user_id] = []
    warnings[user_id].append(reason)

    await ctx.send(f"⚠️ {member.mention} figyelmeztetve lett. Ok: **{reason}**")

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(
            f"⚠️ **Figyelmeztetés**\n"
            f"**Felhasználó:** {member.mention} (`{member.id}`)\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Ok:** {reason}\n"
            f"**Összes figyelmeztetés száma:** {len(warnings[user_id])}"
        )

@bot.command()
@commands.check(is_owner)
async def warns(ctx, member: discord.Member):
    user_id = member.id
    if user_id not in warnings or len(warnings[user_id]) == 0:
        await ctx.send(f"{member.mention} még nem kapott figyelmeztetést.")
    else:
        warn_list = "\n".join([f"{i+1}. {w}" for i, w in enumerate(warnings[user_id])])
        await ctx.send(f"📋 {member.mention} figyelmeztetései:\n{warn_list}")

@bot.command()
@commands.check(is_owner)
async def info(ctx):
    help_message = (
        "**📘 KEPY Moderátor Bot parancsok:**\n"
        "`!ban @név` - Kitiltja a felhasználót.\n"
        "`!kick @név` - Kirúgja a felhasználót.\n"
        "`!mute @név` - Lenémítja a felhasználót (Muted rang).\n"
        "`!unmute @név` - Feloldja a némítást.\n"
        "`!warn @név [ok]` - Figyelmezteti a felhasználót.\n"
        "`!warns @név` - Megmutatja a figyelmeztetéseket.\n"
        "`!lock` - Lezárja az aktuális csatornát.\n"
        "`!unlock` - Feloldja az aktuális csatornát.\n"
        "`!clear szám` - Töröl adott számú üzenetet.\n"
        "Automatikusan törli azokat az üzeneteket, amik `discord.gg/` linket tartalmaznak, és logolja a megadott csatornába.\n"
        "Automatikusan lenémítja a spammereket.\n"
        "🔒 Csak a moderátorok használhatják ezeket."
    )
    await ctx.send(help_message)

@bot.command()
@commands.check(is_owner)
async def lock(ctx, hide: bool = False):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    if hide:
        overwrite.view_channel = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    if hide:
        await ctx.send(f"🔒 {ctx.channel.mention} le lett zárva és el lett rejtve!")
    else:
        await ctx.send(f"🔒 {ctx.channel.mention} le lett zárva!")

@bot.command()
@commands.check(is_owner)
async def unlock(ctx):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    overwrite.view_channel = True
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔓 {ctx.channel.mention} fel lett oldva!")

# Új !clear parancs
@bot.command()
@commands.check(is_owner)
async def clear(ctx, amount: int):
    if amount < 1:
        await ctx.send("⚠️ Adj meg egy számot, ami nagyobb mint 0!")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 = parancs is törlődjön
    await ctx.send(f"🧹 {len(deleted)-1} üzenet törölve.", delete_after=5)

    # Logolás
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(
            f"🧹 **Üzenetek törölve**\n"
            f"**Moderator:** {ctx.author.mention} (`{ctx.author.id}`)\n"
            f"**Csatorna:** {ctx.channel.mention}\n"
            f"**Törölt üzenetek száma:** {len(deleted)-1}"
        )

# Bot token környezeti változóból
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
