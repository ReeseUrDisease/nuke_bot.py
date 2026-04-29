import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import json
from datetime import datetime, timedelta

# ── Config ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")
print(f"Token loaded: {BOT_TOKEN is not None}")
print(f"Token length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")

AUTHORIZED_USER_IDS = [
    933543370935128204,
]

ECONOMY_FILE = "economy.json"
STARTING_BALANCE = 500
DAILY_AMOUNT = 100
DAILY_COOLDOWN_HOURS = 24

# ── Nuke Permission Helper ────────────────────────────────────────────────
def is_nuke_authorized(interaction: discord.Interaction) -> bool:
    return interaction.user.id in AUTHORIZED_USER_IDS

# ── Palette ──────────────────────────────────────────────────────────────────
class C:
    """Centralised colour palette — change once, applies everywhere."""
    PRIMARY    = discord.Color.from_rgb(88,  101, 242)   # Blurple-ish
    SUCCESS    = discord.Color.from_rgb(87,  242, 135)   # Mint green
    WARNING    = discord.Color.from_rgb(254, 231, 92)    # Gold
    DANGER     = discord.Color.from_rgb(237, 66,  69)    # Red
    NEUTRAL    = discord.Color.from_rgb(79,  84,  92)    # Muted grey
    DARK       = discord.Color.from_rgb(32,  34,  37)    # Near-black
    CASINO     = discord.Color.from_rgb(255, 185, 0)     # Casino gold
    PURPLE     = discord.Color.from_rgb(155, 89,  182)   # Purple


# ── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ══════════════════════════════════════════════════════════════════════════════
# 💾 ECONOMY SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
def load_economy():
    if os.path.exists(ECONOMY_FILE):
        with open(ECONOMY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_economy(data):
    with open(ECONOMY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user_data(user_id):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": STARTING_BALANCE, "daily": None, "wins": 0, "losses": 0, "total_won": 0, "total_lost": 0}
        save_economy(data)
    return data[uid]

def get_balance(user_id):
    return get_user_data(user_id)["balance"]

def update_balance(user_id, amount):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": STARTING_BALANCE, "daily": None, "wins": 0, "losses": 0, "total_won": 0, "total_lost": 0}
    data[uid]["balance"] += amount
    if amount > 0:
        data[uid]["wins"] = data[uid].get("wins", 0) + 1
        data[uid]["total_won"] = data[uid].get("total_won", 0) + amount
    else:
        data[uid]["losses"] = data[uid].get("losses", 0) + 1
        data[uid]["total_lost"] = data[uid].get("total_lost", 0) + abs(amount)
    save_economy(data)
    return data[uid]["balance"]

def can_claim_daily(user_id):
    data = load_economy()
    uid = str(user_id)
    if uid not in data or data[uid].get("daily") is None:
        return True, None
    last = datetime.fromisoformat(data[uid]["daily"])
    remaining = timedelta(hours=DAILY_COOLDOWN_HOURS) - (datetime.utcnow() - last)
    if remaining.total_seconds() <= 0:
        return True, None
    return False, remaining

def claim_daily(user_id):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": STARTING_BALANCE, "daily": None, "wins": 0, "losses": 0, "total_won": 0, "total_lost": 0}
    data[uid]["balance"] += DAILY_AMOUNT
    data[uid]["daily"] = datetime.utcnow().isoformat()
    save_economy(data)
    return data[uid]["balance"]

def get_leaderboard():
    data = load_economy()
    sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
    return sorted_users[:10]


# ══════════════════════════════════════════════════════════════════════════════
# 🛠️ SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _base_embed(title: str, description: str = "", color: discord.Color = C.PRIMARY) -> discord.Embed:
    """Returns a clean, styled embed with consistent footer."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="⚡ Powered by ClvrLabs 🍀")
    return embed

async def confirm(ctx, action: str) -> bool:
    embed = _base_embed(
        "⚠️  Confirm Action",
        (
            f"You are about to **{action}**.\n\n"
            "⚠️ This is a destructive action.\n"
            "To proceed, type **CONFIRM** exactly.\n"
            "Anything else or no response in 15 seconds cancels."
        ),
        C.WARNING,
    )
    await ctx.send(embed=embed)

    def check(m):
        return (
            m.author == ctx.author and
            m.channel == ctx.channel
        )

    try:
        reply = await ctx.bot.wait_for(
            "message",
            timeout=15.0,
            check=check
        )

        if reply.content.strip().upper() == "CONFIRM":
            return True

        await ctx.send(
            embed=_base_embed(
                "❌ Cancelled",
                "Confirmation failed.",
                C.NEUTRAL
            ),
            delete_after=5
        )
        return False

    except asyncio.TimeoutError:
        await ctx.send(
            embed=_base_embed(
                "⏱️  Timed Out",
                "No response received — action cancelled.",
                C.NEUTRAL
            ),
            delete_after=5
        )
        return False


async def send_result(ctx, results: list[str]):
    embed = _base_embed(
        "💥  Operation Complete",
        "\n".join(results),
        C.DANGER
    )
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
# 💥 NUKE COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
@bot.command(name="nuke_channels")
async def nuke_channels(ctx):
    if ctx.author.id not in AUTHORIZED_USER_IDS and not ctx.author.guild_permissions.administrator:
    await ctx.send("🚫 You are not authorized to use this command.", delete_after=5)
        return
    if not await confirm(ctx, "delete **ALL** channels"):
        return
    guild = ctx.guild
    count = 0
    for channel in guild.channels:
        try:
            await channel.delete(reason="Nuke: channels")
            count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    try:
        new_ch = await guild.create_text_channel("general")
        embed = _base_embed("💥  Channel Nuke Complete", f"Deleted **{count}** channels.", C.DANGER)
        await new_ch.send(embed=embed)
    except Exception:
        pass

@bot.command(name="nuke_roles")
async def nuke_roles(ctx):
    if ctx.author.id not in AUTHORIZED_USER_IDS and not ctx.author.guild_permissions.administrator:
    await ctx.send("🚫 You are not authorized to use this command.", delete_after=5)
        return
    if not await confirm(ctx, "delete all **roles**"):
        return
    guild = ctx.guild
    count = 0
    for role in guild.roles:
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: roles")
            count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    await send_result(ctx, [f"🗑️  Deleted **{count}** roles."])

@bot.command(name="nuke_channels_roles")
async def nuke_channels_roles(ctx):
    if ctx.author.id not in AUTHORIZED_USER_IDS and not ctx.author.guild_permissions.administrator:
    await ctx.send("🚫 You are not authorized to use this command.", delete_after=5)
        return
    if not await confirm(ctx, "delete all channels **and** roles"):
        return
    guild = ctx.guild
    ch_count = role_count = 0
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: channels+roles")
            ch_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: channels+roles")
            role_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    try:
        new_ch = await guild.create_text_channel("general")
        embed = _base_embed("💥  Nuke Complete", f"🗑️  Channels removed: **{ch_count}**\n🎭  Roles removed: **{role_count}**", C.DANGER)
        await new_ch.send(embed=embed)
    except Exception:
        pass

@bot.command(name="nuke_kick")
async def nuke_kick(ctx):
    if ctx.author.id not in AUTHORIZED_USER_IDS and not ctx.author.guild_permissions.administrator:
    await ctx.send("🚫 You are not authorized to use this command.", delete_after=5)
        return
    if not await confirm(ctx, "delete channels, roles, **and kick all members**"):
        return
    guild = ctx.guild
    ch_count = role_count = kick_count = 0
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: kick")
            ch_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: kick")
            role_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    async for member in guild.fetch_members(limit=None):
        if member == ctx.author:
            continue
        try:
            await member.kick(reason="Nuke: kick all")
            kick_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    try:
        new_ch = await guild.create_text_channel("general")
        embed = _base_embed(
            "💥  Full Nuke Complete",
            f"🗑️  Channels: **{ch_count}**\n🎭  Roles: **{role_count}**\n👢  Members kicked: **{kick_count}**",
            C.DANGER,
        )
        await new_ch.send(embed=embed)
    except Exception:
        pass

@bot.command(name="nuke_full")
async def nuke_full(ctx):
    if ctx.author.id not in AUTHORIZED_USER_IDS and not ctx.author.guild_permissions.administrator:
    await ctx.send("🚫 You are not authorized to use this command.", delete_after=5)
        return
    if not await confirm(ctx, "perform a **FULL RESET** — channels, roles, emojis, and kick all members"):
        return
    guild = ctx.guild
    ch_count = role_count = kick_count = emoji_count = 0
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: full reset")
            ch_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: full reset")
            role_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for emoji in list(guild.emojis):
        try:
            await emoji.delete(reason="Nuke: full reset")
            emoji_count += 1
            await asyncio.sleep(0.005)
        except (discord.Forbidden, discord.HTTPException):
            pass
    async for member in guild.fetch_members(limit=None):
        if member == ctx.author:
            continue
        try:
            await member.kick(reason="Nuke: full reset")
            kick_count += 1
            await asyncio.sleep(0.1)
        except (discord.Forbidden, discord.HTTPException):
            pass
    try:
        new_ch = await guild.create_text_channel("general")
        embed = _base_embed(
            "💥  Full Server Nuke",
            f"🗑️  Channels: **{ch_count}**\n🎭  Roles: **{role_count}**\n😀  Emojis: **{emoji_count}**\n👢  Members kicked: **{kick_count}**",
            C.DANGER,
        )
        await new_ch.send(embed=embed)
    except Exception:
        pass

@bot.command(name="nuke_help")
async def nuke_help(ctx):
    embed = _base_embed("💥  Nuke Commands", color=C.DANGER)
    embed.add_field(name="!nuke_channels",       value="Delete all channels",                          inline=False)
    embed.add_field(name="!nuke_roles",          value="Delete all non-default roles",                  inline=False)
    embed.add_field(name="!nuke_channels_roles", value="Delete all channels and roles",                 inline=False)
    embed.add_field(name="!nuke_kick",           value="Delete channels, roles, and kick all members", inline=False)
    embed.add_field(name="!nuke_full",           value="Full reset: channels, roles, emojis, members", inline=False)
    embed.set_footer(text="⚠️  Requires Administrator · All actions ask for ation.")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
# 🔒 SECURITY / MODERATION COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

def _mod_check(interaction: discord.Interaction, permission: str = None):
    return interaction.user.id == 1278035697416146966

# ── /ban ──────────────────────────────────────────────────────────────────────
@tree.command(name="ban", description="Ban a member from the server.")
@app_commands.describe(
    member="Member to ban",
    reason="Reason for the ban",
    delete_days="Days of messages to delete (0–7, default 0)",
)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
    delete_days: int = 0,
):
    if not _mod_check(interaction, "ban_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Ban Members** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    if member == interaction.user:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You cannot ban yourself.", C.DANGER), ephemeral=True
        )
        return
    if member.top_role >= interaction.user.top_role and interaction.user.id not in AUTHORIZED_USER_IDS:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You cannot ban someone with an equal or higher role.", C.DANGER),
            ephemeral=True,
        )
        return

    delete_days = max(0, min(7, delete_days))
    try:
        await member.ban(reason=f"{reason} — banned by {interaction.user}", delete_message_days=delete_days)
        embed = _base_embed(
            "🔨  Member Banned",
            f"> **User:** {member.mention} (`{member}`)\n> **Reason:** {reason}\n> **Moderator:** {interaction.user.mention}",
            C.DANGER,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=_base_embed("❌  Failed", "I don't have permission to ban that member.", C.DANGER), ephemeral=True
        )

# ── /unban ────────────────────────────────────────────────────────────────────
@tree.command(name="unban", description="Unban a user by their ID.")
@app_commands.describe(user_id="The user's Discord ID", reason="Reason for the unban")
async def unban(interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
    if not _mod_check(interaction, "ban_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Ban Members** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    try:
        uid = int(user_id)
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user, reason=f"{reason} — unbanned by {interaction.user}")
        embed = _base_embed(
            "✅  Member Unbanned",
            f"> **User:** `{user}` (`{uid}`)\n> **Reason:** {reason}\n> **Moderator:** {interaction.user.mention}",
            C.SUCCESS,
        )
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)
    except ValueError:
        await interaction.response.send_message(
            embed=_base_embed("❌  Invalid ID", "Please provide a valid numeric user ID.", C.DANGER), ephemeral=True
        )
    except discord.NotFound:
        await interaction.response.send_message(
            embed=_base_embed("❌  Not Found", "That user is not banned or doesn't exist.", C.DANGER), ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=_base_embed("❌  Failed", "I don't have permission to unban.", C.DANGER), ephemeral=True
        )

# ── /kick ─────────────────────────────────────────────────────────────────────
@tree.command(name="kick", description="Kick a member from the server.")
@app_commands.describe(member="Member to kick", reason="Reason for the kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not _mod_check(interaction, "kick_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Kick Members** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    if member == interaction.user:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You cannot kick yourself.", C.DANGER), ephemeral=True
        )
        return
    if member.top_role >= interaction.user.top_role and interaction.user.id not in AUTHORIZED_USER_IDS:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You cannot kick someone with an equal or higher role.", C.DANGER),
            ephemeral=True,
        )
        return
    try:
        await member.kick(reason=f"{reason} — kicked by {interaction.user}")
        embed = _base_embed(
            "👢  Member Kicked",
            f"> **User:** {member.mention} (`{member}`)\n> **Reason:** {reason}\n> **Moderator:** {interaction.user.mention}",
            C.WARNING,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=_base_embed("❌  Failed", "I don't have permission to kick that member.", C.DANGER), ephemeral=True
        )

# ── /timeout ──────────────────────────────────────────────────────────────────
@tree.command(name="timeout", description="Timeout a member (mutes them for a set duration).")
@app_commands.describe(
    member="Member to timeout",
    minutes="Duration in minutes (1–40320 / up to 28 days)",
    reason="Reason for the timeout",
)
async def timeout_member(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: int = 10,
    reason: str = "No reason provided",
):
    if not _mod_check(interaction, "moderate_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Moderate Members** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    if member == interaction.user:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You cannot timeout yourself.", C.DANGER), ephemeral=True
        )
        return
    if member.top_role >= interaction.user.top_role and interaction.user.id not in AUTHORIZED_USER_IDS:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You cannot timeout someone with an equal or higher role.", C.DANGER),
            ephemeral=True,
        )
        return

    minutes = max(1, min(40320, minutes))
    until = discord.utils.utcnow() + timedelta(minutes=minutes)

    try:
        await member.timeout(until, reason=f"{reason} — timed out by {interaction.user}")
        hours, mins = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        duration_str = ""
        if days:   duration_str += f"{days}d "
        if hours:  duration_str += f"{hours}h "
        duration_str += f"{mins}m"

        embed = _base_embed(
            "⏱️  Member Timed Out",
            f"> **User:** {member.mention} (`{member}`)\n> **Duration:** {duration_str.strip()}\n> **Reason:** {reason}\n> **Moderator:** {interaction.user.mention}\n> **Expires:** <t:{int(until.timestamp())}:R>",
            C.WARNING,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=_base_embed("❌  Failed", "I don't have permission to timeout that member.", C.DANGER), ephemeral=True
        )

# ── /untimeout ────────────────────────────────────────────────────────────────
@tree.command(name="untimeout", description="Remove a timeout from a member.")
@app_commands.describe(member="Member to remove the timeout from", reason="Reason")
async def untimeout_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
):
    if not _mod_check(interaction, "moderate_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Moderate Members** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    try:
        await member.timeout(None, reason=f"{reason} — timeout removed by {interaction.user}")
        embed = _base_embed(
            "✅  Timeout Removed",
            f"> **User:** {member.mention} (`{member}`)\n> **Reason:** {reason}\n> **Moderator:** {interaction.user.mention}",
            C.SUCCESS,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=_base_embed("❌  Failed", "I don't have permission to remove that timeout.", C.DANGER), ephemeral=True
        )

# ── /warn ─────────────────────────────────────────────────────────────────────
WARNINGS: dict[str, list[dict]] = {}   # { "guild_id:user_id": [{reason, mod, time}] }

def _warn_key(guild_id, user_id):
    return f"{guild_id}:{user_id}"

@tree.command(name="warn", description="Issue a formal warning to a member.")
@app_commands.describe(member="Member to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not _mod_check(interaction, "kick_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Kick Members** permission to warn.", C.DANGER),
            ephemeral=True,
        )
        return
    key = _warn_key(interaction.guild_id, member.id)
    WARNINGS.setdefault(key, []).append({
        "reason": reason,
        "mod": str(interaction.user),
        "time": datetime.utcnow().isoformat(),
    })
    count = len(WARNINGS[key])

    embed = _base_embed(
        "⚠️  Warning Issued",
        f"> **User:** {member.mention} (`{member}`)\n> **Reason:** {reason}\n> **Moderator:** {interaction.user.mention}\n> **Total Warnings:** {count}",
        C.WARNING,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

    try:
        dm_embed = _base_embed(
            f"⚠️  You received a warning in {interaction.guild.name}",
            f"> **Reason:** {reason}\n> **Moderator:** {interaction.user}\n> **Total Warnings:** {count}",
            C.WARNING,
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

# ── /warnings ─────────────────────────────────────────────────────────────────
@tree.command(name="warnings", description="View all warnings for a member.")
@app_commands.describe(member="Member to check warnings for")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    if not _mod_check(interaction, "kick_members"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Kick Members** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    key = _warn_key(interaction.guild_id, member.id)
    user_warns = WARNINGS.get(key, [])
    if not user_warns:
        await interaction.response.send_message(
            embed=_base_embed("✅  No Warnings", f"{member.mention} has a clean record.", C.SUCCESS)
        )
        return

    embed = _base_embed(f"⚠️  Warnings for {member.display_name}", color=C.WARNING)
    embed.set_thumbnail(url=member.display_avatar.url)
    for i, w in enumerate(user_warns, 1):
        ts = datetime.fromisoformat(w["time"]).strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(
            name=f"Warning #{i}  ·  {ts}",
            value=f"**Reason:** {w['reason']}\n**Moderator:** {w['mod']}",
            inline=False,
        )
    embed.set_footer(text=f"Total warnings: {len(user_warns)}")
    await interaction.response.send_message(embed=embed)

# ── /clearwarnings ────────────────────────────────────────────────────────────
@tree.command(name="clearwarnings", description="Clear all warnings for a member.")
@app_commands.describe(member="Member whose warnings to clear")
async def clearwarnings(interaction: discord.Interaction, member: discord.Member):
    if not _mod_check(interaction, "administrator"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Administrator** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    key = _warn_key(interaction.guild_id, member.id)
    WARNINGS.pop(key, None)
    await interaction.response.send_message(
        embed=_base_embed("🗑️  Warnings Cleared", f"All warnings for {member.mention} have been removed.", C.SUCCESS)
    )

# ── /purge ────────────────────────────────────────────────────────────────────
@tree.command(name="purge", description="Bulk-delete messages from a channel.")
@app_commands.describe(
    amount="Number of messages to delete (1–100)",
    member="Only delete messages from this member (optional)",
)
async def purge(interaction: discord.Interaction, amount: int, member: discord.Member = None):
    if not _mod_check(interaction, "manage_messages"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Manage Messages** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    amount = max(1, min(100, amount))
    await interaction.response.defer(ephemeral=True)

    def check(msg):
        return member is None or msg.author == member

    deleted = await interaction.channel.purge(limit=amount, check=check)
    desc = f"Deleted **{len(deleted)}** message{'s' if len(deleted) != 1 else ''}"
    if member:
        desc += f" from {member.mention}"
    desc += f" in {interaction.channel.mention}."
    await interaction.followup.send(
        embed=_base_embed("🧹  Purge Complete", desc, C.SUCCESS), ephemeral=True
    )

# ── /slowmode ─────────────────────────────────────────────────────────────────
@tree.command(name="slowmode", description="Set slowmode delay for the current channel.")
@app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600)")
async def slowmode(interaction: discord.Interaction, seconds: int = 0):
    if not _mod_check(interaction, "manage_channels"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Manage Channels** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    seconds = max(0, min(21600, seconds))
    await interaction.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        msg = f"Slowmode has been **disabled** in {interaction.channel.mention}."
    else:
        msg = f"Slowmode set to **{seconds}s** in {interaction.channel.mention}."
    await interaction.response.send_message(embed=_base_embed("🐢  Slowmode Updated", msg, C.PRIMARY))

# ── /lock / /unlock ───────────────────────────────────────────────────────────
@tree.command(name="lock", description="Lock a channel so members cannot send messages.")
@app_commands.describe(channel="Channel to lock (defaults to current)", reason="Reason")
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
    if not _mod_check(interaction, "manage_channels"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Manage Channels** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    ch = channel or interaction.channel
    overwrite = ch.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await ch.edit(overwrites={interaction.guild.default_role: overwrite}, reason=reason)
    embed = _base_embed("🔒  Channel Locked", f"{ch.mention} has been locked.\n> **Reason:** {reason}", C.DANGER)
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

@tree.command(name="unlock", description="Unlock a previously locked channel.")
@app_commands.describe(channel="Channel to unlock (defaults to current)", reason="Reason")
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
    if not _mod_check(interaction, "manage_channels"):
        await interaction.response.send_message(
            embed=_base_embed("🚫  Permission Denied", "You need **Manage Channels** permission.", C.DANGER),
            ephemeral=True,
        )
        return
    ch = channel or interaction.channel
    overwrite = ch.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await ch.edit(overwrites={interaction.guild.default_role: overwrite}, reason=reason)
    embed = _base_embed("🔓  Channel Unlocked", f"{ch.mention} is now open.\n> **Reason:** {reason}", C.SUCCESS)
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

# ── /userinfo ─────────────────────────────────────────────────────────────────
@tree.command(name="userinfo", description="Display detailed information about a member.")
@app_commands.describe(member="Member to inspect (defaults to yourself)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    roles = [r.mention for r in reversed(member.roles) if not r.is_default()]
    key = _warn_key(interaction.guild_id, member.id)
    warn_count = len(WARNINGS.get(key, []))

    embed = _base_embed(f"👤  {member.display_name}", color=member.color if member.color.value else C.PRIMARY)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username",     value=f"`{member}`",                                       inline=True)
    embed.add_field(name="ID",           value=f"`{member.id}`",                                    inline=True)
    embed.add_field(name="Bot",          value="Yes" if member.bot else "No",                        inline=True)
    embed.add_field(name="Joined Server",value=f"<t:{int(member.joined_at.timestamp())}:R>",         inline=True)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>",    inline=True)
    embed.add_field(name="⚠️ Warnings",  value=str(warn_count),                                     inline=True)
    embed.add_field(
        name=f"Roles ({len(roles)})",
        value=" ".join(roles[:10]) + (" ..." if len(roles) > 10 else "") if roles else "None",
        inline=False,
    )
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

# ── /serverinfo ───────────────────────────────────────────────────────────────
@tree.command(name="serverinfo", description="Display information about this server.")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = _base_embed(g.name, color=C.PRIMARY)
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner",        value=f"<@{g.owner_id}>",                                  inline=True)
    embed.add_field(name="Members",      value=f"**{g.member_count:,}**",                            inline=True)
    embed.add_field(name="Channels",     value=f"**{len(g.channels)}**",                             inline=True)
    embed.add_field(name="Roles",        value=f"**{len(g.roles)}**",                               inline=True)
    embed.add_field(name="Boost Level",  value=f"**{g.premium_tier}** ({g.premium_subscription_count} boosts)", inline=True)
    embed.add_field(name="Created",      value=f"<t:{int(g.created_at.timestamp())}:R>",             inline=True)
    embed.add_field(name="Server ID",    value=f"`{g.id}`",                                         inline=False)
    embed.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=embed)

# ── /mod_help ─────────────────────────────────────────────────────────────────
@tree.command(name="mod_help", description="Show all moderation commands.")
async def mod_help(interaction: discord.Interaction):
    embed = _base_embed("🛡️  Moderation Commands", color=C.PRIMARY)
    commands_info = [
        ("/ban",           "Ban a member · `member, reason, delete_days`"),
        ("/unban",         "Unban a user by ID · `user_id, reason`"),
        ("/kick",          "Kick a member · `member, reason`"),
        ("/timeout",       "Mute a member temporarily · `member, minutes, reason`"),
        ("/untimeout",     "Remove a timeout · `member, reason`"),
        ("/warn",          "Issue a formal warning · `member, reason`"),
        ("/warnings",      "View warnings for a member · `member`"),
        ("/clearwarnings", "Clear all warnings · `member`"),
        ("/purge",         "Bulk-delete messages · `amount, member?`"),
        ("/slowmode",      "Set channel slowmode · `seconds`"),
        ("/lock",          "Lock a channel · `channel?, reason`"),
        ("/unlock",        "Unlock a channel · `channel?, reason`"),
        ("/userinfo",      "Info about a member · `member?`"),
        ("/serverinfo",    "Info about the server"),
    ]
    for name, desc in commands_info:
        embed.add_field(name=name, value=desc, inline=False)
    embed.set_footer(text="⚡ Requires appropriate permissions for each command.")
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
# 💰 ECONOMY COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="balance", description="Check your balance and stats!")
async def balance(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    bal       = user_data["balance"]
    wins      = user_data.get("wins", 0)
    losses    = user_data.get("losses", 0)
    total_won = user_data.get("total_won", 0)
    total_lost= user_data.get("total_lost", 0)
    winrate   = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0

    embed = _base_embed(f"💰  {interaction.user.display_name}'s Wallet", color=C.SUCCESS)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="💵 Balance",    value=f"**${bal:,}**",        inline=True)
    embed.add_field(name="📈 Win Rate",   value=f"**{winrate}%**",      inline=True)
    embed.add_field(name="🏆 Wins",       value=f"**{wins}**",          inline=True)
    embed.add_field(name="💔 Losses",     value=f"**{losses}**",        inline=True)
    embed.add_field(name="💸 Total Won",  value=f"**${total_won:,}**",  inline=True)
    embed.add_field(name="🔥 Total Lost", value=f"**${total_lost:,}**", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="daily", description="Claim your daily $100!")
async def daily(interaction: discord.Interaction):
    can_claim, remaining = can_claim_daily(interaction.user.id)
    if can_claim:
        new_bal = claim_daily(interaction.user.id)
        embed = _base_embed(
            "💸  Daily Reward Claimed!",
            f"You claimed **${DAILY_AMOUNT}**!\n\n💰  New balance: **${new_bal:,}**\n_Come back in 24 hours!_",
            C.SUCCESS,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
    else:
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        embed = _base_embed(
            "⏱️  Already Claimed",
            f"Come back in **{hours}h {minutes}m**!",
            C.DANGER,
        )
    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="See the richest players!")
async def leaderboard(interaction: discord.Interaction):
    top = get_leaderboard()
    embed = _base_embed("🏆  Richest Players", color=C.CASINO)
    medals = ["🥇", "🥈", "🥉"]
    description = ""
    for i, (uid, info) in enumerate(top):
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        try:
            user = await bot.fetch_user(int(uid))
            name = user.display_name
        except Exception:
            name = f"User {uid}"
        winrate = round(
            (info.get("wins", 0) / max(info.get("wins", 0) + info.get("losses", 0), 1)) * 100, 1
        )
        description += f"{medal}  **{name}** — ${info['balance']:,}  _(WR: {winrate}%)_\n"
    embed.description = description or "No players yet!"
    embed.set_footer(text="Play games to earn money and climb the leaderboard!")
    await interaction.response.send_message(embed=embed)

@tree.command(name="give", description="Give money to another player!")
@app_commands.describe(user="Who to give money to", amount="How much to give")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    if user == interaction.user:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "You can't give money to yourself!", C.DANGER), ephemeral=True
        )
        return
    if amount <= 0:
        await interaction.response.send_message(
            embed=_base_embed("❌  Error", "Amount must be more than $0!", C.DANGER), ephemeral=True
        )
        return
    bal = get_balance(interaction.user.id)
    if amount > bal:
        await interaction.response.send_message(
            embed=_base_embed("❌  Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True
        )
        return
    update_balance(interaction.user.id, -amount)
    update_balance(user.id, amount)
    embed = _base_embed(
        "💸  Money Sent!",
        f"{interaction.user.mention} sent **${amount:,}** to {user.mention}!",
        C.SUCCESS,
    )
    embed.add_field(name="Your new balance", value=f"**${get_balance(interaction.user.id):,}**", inline=True)
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
# 🎮 INTERACTIVE GAMES
# ══════════════════════════════════════════════════════════════════════════════

# ── 🎰 SLOTS ──────────────────────────────────────────────────────────────────
class SlotsView(discord.ui.View):
    def __init__(self, user, bet):
        super().__init__(timeout=60)
        self.user = user
        self.bet = bet
        self.spins_left = 3

    def spin_reels(self):
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
        weights = [30, 25, 20, 15, 6, 3, 1]
        return random.choices(symbols, weights=weights, k=3)

    def calculate_win(self, reels):
        if reels[0] == reels[1] == reels[2]:
            multipliers = {"💎": 20, "7️⃣": 15, "⭐": 10}
            return multipliers.get(reels[0], 5), True
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            return 1, False
        return 0, False

    def build_embed(self, reels, result_text, color):
        embed = _base_embed("🎰  Slot Machine", color=color)
        embed.add_field(name="Reels",       value=f"# {' | '.join(reels)}", inline=False)
        embed.add_field(name="Result",      value=result_text,              inline=False)
        embed.add_field(name="💵 Bet",      value=f"**${self.bet:,}**",     inline=True)
        embed.add_field(name="🔄 Spins Left",value=f"**{self.spins_left}**",inline=True)
        embed.add_field(name="💰 Balance",  value=f"**${get_balance(self.user.id):,}**", inline=True)
        return embed

    @discord.ui.button(label="🎰 Spin!", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        reels = self.spin_reels()
        multiplier, jackpot = self.calculate_win(reels)
        self.spins_left -= 1

        if multiplier > 1:
            winnings = self.bet * multiplier
            update_balance(self.user.id, winnings)
            if jackpot:
                result = f"🎉  **JACKPOT! {multiplier}x!** You won **${winnings:,}**!"
                color = C.CASINO
            else:
                result = f"🎊  **{multiplier}x multiplier!** You won **${winnings:,}**!"
                color = C.SUCCESS
        elif multiplier == 1:
            result = f"😐  **Two of a kind!** Bet returned **${self.bet:,}**"
            color = C.WARNING
        else:
            update_balance(self.user.id, -self.bet)
            result = f"❌  **No match!** Lost **${self.bet:,}**"
            color = C.DANGER

        if self.spins_left <= 0 or get_balance(self.user.id) < self.bet:
            button.disabled = True
            self.stop()

        embed = self.build_embed(reels, result, color)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.red)
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        embed = _base_embed(
            "🎰  Cashed Out!",
            f"Thanks for playing!\nYour balance: **${get_balance(self.user.id):,}**",
            C.PRIMARY,
        )
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

@tree.command(name="slots", description="Spin the slot machine!")
@app_commands.describe(bet="Amount to bet per spin (default: 10)")
async def slots(interaction: discord.Interaction, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Bet must be more than $0!", C.DANGER), ephemeral=True); return
    if bet > bal:
        await interaction.response.send_message(embed=_base_embed("❌ Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True); return

    view = SlotsView(interaction.user, bet)
    embed = _base_embed("🎰  Slot Machine", color=C.PRIMARY)
    embed.add_field(name="💵 Bet",        value=f"**${bet:,}** per spin",  inline=True)
    embed.add_field(name="🔄 Free Spins", value="**3**",                   inline=True)
    embed.add_field(name="💰 Balance",    value=f"**${bal:,}**",           inline=True)
    embed.add_field(name="Payouts", value="💎 = 20x  ·  7️⃣ = 15x  ·  ⭐ = 10x\n🍇 = 5x  ·  Two of a kind = return bet", inline=False)
    embed.set_footer(text="Press Spin to start!")
    await interaction.response.send_message(embed=embed, view=view)


# ── 🪨 ROCK PAPER SCISSORS ────────────────────────────────────────────────────
class RPSView(discord.ui.View):
    def __init__(self, user, bet):
        super().__init__(timeout=60)
        self.user = user
        self.bet = bet
        self.player_wins = 0
        self.bot_wins = 0
        self.round = 1
        self.max_rounds = 3

    def play_round(self, choice):
        options = ["rock", "paper", "scissors"]
        emojis  = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        bot_choice = random.choice(options)
        if choice == bot_choice:
            outcome = "tie"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            outcome = "win"; self.player_wins += 1
        else:
            outcome = "loss"; self.bot_wins += 1
        return emojis[choice], emojis[bot_choice], outcome

    def build_embed(self, player_emoji, bot_emoji, outcome, round_result):
        color = C.SUCCESS if outcome == "win" else C.DANGER if outcome == "loss" else C.WARNING
        embed = _base_embed(f"🪨  Rock Paper Scissors — Round {self.round - 1}/{self.max_rounds}", color=color)
        embed.add_field(name="Your Pick",  value=player_emoji,   inline=True)
        embed.add_field(name="Bot's Pick", value=bot_emoji,      inline=True)
        embed.add_field(name="Round",      value=round_result,   inline=True)
        embed.add_field(name="Score",  value=f"You **{self.player_wins}** — Bot **{self.bot_wins}**", inline=False)
        embed.add_field(name="💵 Bet",     value=f"**${self.bet:,}**",                               inline=True)
        embed.add_field(name="💰 Balance", value=f"**${get_balance(self.user.id):,}**",               inline=True)
        return embed

    async def handle_choice(self, interaction, choice):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        player_emoji, bot_emoji, outcome = self.play_round(choice)
        self.round += 1
        round_result = "🎉 You win this round!" if outcome == "win" else "❌ Bot wins this round!" if outcome == "loss" else "🤝 Tie!"
        embed = self.build_embed(player_emoji, bot_emoji, outcome, round_result)
        game_over = self.round > self.max_rounds or self.player_wins == 2 or self.bot_wins == 2
        if game_over:
            for child in self.children: child.disabled = True
            self.stop()
            if self.player_wins > self.bot_wins:
                new_bal = update_balance(self.user.id, self.bet * 2)
                embed.add_field(name="🏆 GAME OVER", value=f"**You won the match! +${self.bet * 2:,}**\nBalance: **${new_bal:,}**", inline=False)
                embed.color = C.CASINO
            elif self.bot_wins > self.player_wins:
                new_bal = update_balance(self.user.id, -self.bet)
                embed.add_field(name="💔 GAME OVER", value=f"**Bot wins the match! -${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
                embed.color = C.DANGER
            else:
                embed.add_field(name="🤝 GAME OVER", value=f"**It's a draw! Bet returned.**\nBalance: **${get_balance(self.user.id):,}**", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🪨 Rock",     style=discord.ButtonStyle.grey)
    async def rock(self, interaction, button):     await self.handle_choice(interaction, "rock")
    @discord.ui.button(label="📄 Paper",    style=discord.ButtonStyle.blurple)
    async def paper(self, interaction, button):    await self.handle_choice(interaction, "paper")
    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.red)
    async def scissors(self, interaction, button): await self.handle_choice(interaction, "scissors")

@tree.command(name="rps", description="Play Best of 3 Rock Paper Scissors!")
@app_commands.describe(bet="Amount to bet (default: 10)")
async def rps(interaction: discord.Interaction, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Bet must be more than $0!", C.DANGER), ephemeral=True); return
    if bet > bal:
        await interaction.response.send_message(embed=_base_embed("❌ Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True); return
    view = RPSView(interaction.user, bet)
    embed = _base_embed("🪨  Rock Paper Scissors — Best of 3!", color=C.PRIMARY)
    embed.add_field(name="💵 Bet",    value=f"**${bet:,}**",        inline=True)
    embed.add_field(name="🏆 Win",    value=f"**+${bet * 2:,}**",   inline=True)
    embed.add_field(name="💔 Lose",   value=f"**-${bet:,}**",       inline=True)
    embed.add_field(name="Rules", value="Win 2 out of 3 rounds to take the prize!\nTied rounds don't count.", inline=False)
    embed.set_footer(text="Choose your weapon!")
    await interaction.response.send_message(embed=embed, view=view)


# ── 🎱 8 BALL ─────────────────────────────────────────────────────────────────
class EightBallView(discord.ui.View):
    def __init__(self, user, question, bet):
        super().__init__(timeout=30)
        self.user = user
        self.question = question
        self.bet = bet

    @discord.ui.button(label="🎱 Reveal Answer", style=discord.ButtonStyle.blurple)
    async def reveal(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        positive = ["✅ It is certain.", "✅ It is decidedly so.", "✅ Without a doubt.", "✅ Yes, definitely.", "✅ You may rely on it.", "✅ As I see it, yes.", "✅ Most likely.", "✅ Outlook good.", "✅ Yes.", "✅ Signs point to yes."]
        neutral  = ["🤷 Reply hazy, try again.", "🤷 Ask again later.", "🤷 Better not tell you now.", "🤷 Cannot predict now.", "🤷 Concentrate and ask again."]
        negative = ["❌ Don't count on it.", "❌ My reply is no.", "❌ My sources say no.", "❌ Outlook not so good.", "❌ Very doubtful."]
        answer = random.choice(positive + neutral + negative)
        if answer in positive:
            winnings = self.bet * 2
            new_bal  = update_balance(self.user.id, winnings)
            result, color = f"🎉  **YES answer!** You win **${winnings:,}**!", C.SUCCESS
        elif answer in neutral:
            new_bal = get_balance(self.user.id)
            result, color = "🤷  **Neutral!** Bet returned.", C.WARNING
        else:
            new_bal = update_balance(self.user.id, -self.bet)
            result, color = f"❌  **NO answer!** Lost **${self.bet:,}**!", C.DANGER

        embed = _base_embed("🎱  The Magic 8 Ball Speaks...", color=color)
        embed.add_field(name="❓ Your Question", value=self.question,          inline=False)
        embed.add_field(name="🎱 The Answer",    value=f"**{answer}**",        inline=False)
        embed.add_field(name="💰 Result",        value=result,                 inline=False)
        embed.add_field(name="💵 Balance",       value=f"**${new_bal:,}**",    inline=True)
        button.disabled = True; self.stop()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        self.stop()
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(
            embed=_base_embed("🎱  8 Ball Cancelled", "The spirits were not consulted.", C.NEUTRAL), view=self
        )

@tree.command(name="8ball", description="Ask the magic 8 ball and bet on a YES answer!")
@app_commands.describe(question="Your yes/no question", bet="Amount to bet (default: 10)")
async def eightball(interaction: discord.Interaction, question: str, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Bet must be more than $0!", C.DANGER), ephemeral=True); return
    if bet > bal:
        await interaction.response.send_message(embed=_base_embed("❌ Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True); return
    view = EightBallView(interaction.user, question, bet)
    embed = _base_embed("🎱  Magic 8 Ball", color=C.PURPLE)
    embed.add_field(name="❓ Question",  value=question,               inline=False)
    embed.add_field(name="💵 Bet",       value=f"**${bet:,}** on YES", inline=True)
    embed.add_field(name="🏆 Win",       value=f"**+${bet * 2:,}**",   inline=True)
    embed.add_field(name="🤷 Neutral",   value="Bet returned",         inline=True)
    embed.add_field(name="❌ Lose",      value=f"**-${bet:,}**",       inline=True)
    embed.set_footer(text="Press Reveal Answer when you're ready...")
    await interaction.response.send_message(embed=embed, view=view)


# ── 🎲 DICE ───────────────────────────────────────────────────────────────────
class DiceView(discord.ui.View):
    def __init__(self, user, bet, sides):
        super().__init__(timeout=60)
        self.user = user; self.bet = bet; self.sides = sides
        self.rounds_left = 3; self.player_score = 0; self.bot_score = 0

    @discord.ui.button(label="🎲 Roll!", style=discord.ButtonStyle.green)
    async def roll(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        player_roll = random.randint(1, self.sides)
        bot_roll    = random.randint(1, self.sides)
        self.rounds_left -= 1
        if player_roll > bot_roll:
            self.player_score += 1
            round_result, color = f"🎉 You win this roll! (**{player_roll}** vs **{bot_roll}**)", C.SUCCESS
        elif bot_roll > player_roll:
            self.bot_score += 1
            round_result, color = f"❌ Bot wins this roll! (**{player_roll}** vs **{bot_roll}**)", C.DANGER
        else:
            round_result, color = f"🤝 Tie! (**{player_roll}** vs **{bot_roll}**)", C.WARNING

        embed = _base_embed(f"🎲  Dice Duel (d{self.sides})", color=color)
        embed.add_field(name="🎲 This Roll",  value=round_result,                                          inline=False)
        embed.add_field(name="📊 Score",      value=f"You **{self.player_score}** — Bot **{self.bot_score}**", inline=True)
        embed.add_field(name="🔄 Rolls Left", value=f"**{self.rounds_left}**",                              inline=True)
        embed.add_field(name="💵 Bet",        value=f"**${self.bet:,}**",                                   inline=True)

        if self.rounds_left <= 0:
            button.disabled = True; self.stop()
            if self.player_score > self.bot_score:
                new_bal = update_balance(self.user.id, self.bet * 2)
                embed.add_field(name="🏆 GAME OVER", value=f"**You win! +${self.bet * 2:,}**\nBalance: **${new_bal:,}**", inline=False)
                embed.color = C.CASINO
            elif self.bot_score > self.player_score:
                new_bal = update_balance(self.user.id, -self.bet)
                embed.add_field(name="💔 GAME OVER", value=f"**Bot wins! -${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
                embed.color = C.DANGER
            else:
                embed.add_field(name="🤝 GAME OVER", value=f"**Draw! Bet returned.**\nBalance: **${get_balance(self.user.id):,}**", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

@tree.command(name="dice", description="Play a 3-round Dice Duel!")
@app_commands.describe(sides="Number of sides on the dice (default: 6)", bet="Amount to bet (default: 10)")
async def dice(interaction: discord.Interaction, sides: int = 6, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if sides < 2 or sides > 100:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Sides must be between 2 and 100!", C.DANGER), ephemeral=True); return
    if bet <= 0:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Bet must be more than $0!", C.DANGER), ephemeral=True); return
    if bet > bal:
        await interaction.response.send_message(embed=_base_embed("❌ Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True); return
    view = DiceView(interaction.user, bet, sides)
    embed = _base_embed(f"🎲  Dice Duel — d{sides}", color=C.PRIMARY)
    embed.add_field(name="💵 Bet",    value=f"**${bet:,}**",        inline=True)
    embed.add_field(name="🔄 Rounds", value="**3**",                 inline=True)
    embed.add_field(name="🏆 Win",    value=f"**+${bet * 2:,}**",   inline=True)
    embed.add_field(name="Rules", value=f"Roll a d{sides} against the bot 3 times.\nHighest score after 3 rounds wins!", inline=False)
    embed.set_footer(text="Press Roll to start!")
    await interaction.response.send_message(embed=embed, view=view)


# ── ❓ TRIVIA ─────────────────────────────────────────────────────────────────
TRIVIA_QUESTIONS = {
    "easy": [
        {"q": "What is the capital of France?", "a": "paris", "reward": 50},
        {"q": "How many sides does a hexagon have?", "a": "6", "reward": 50},
        {"q": "What color is the sky on a clear day?", "a": "blue", "reward": 50},
        {"q": "How many legs does a spider have?", "a": "8", "reward": 50},
        {"q": "What is the largest planet in our solar system?", "a": "jupiter", "reward": 50},
        {"q": "What is the capital of Japan?", "a": "tokyo", "reward": 50},
        {"q": "How many continents are there?", "a": "7", "reward": 50},
        {"q": "What is the fastest land animal?", "a": "cheetah", "reward": 50},
        {"q": "What planet is known as the Red Planet?", "a": "mars", "reward": 50},
        {"q": "What is 7 x 8?", "a": "56", "reward": 50},
        {"q": "What is the capital of Italy?", "a": "rome", "reward": 50},
        {"q": "How many days are in a week?", "a": "7", "reward": 50},
        {"q": "What color are bananas?", "a": "yellow", "reward": 50},
        {"q": "What do bees make?", "a": "honey", "reward": 50},
        {"q": "What is 10 + 5?", "a": "15", "reward": 50},
        {"q": "What is the opposite of hot?", "a": "cold", "reward": 50},
        {"q": "What shape has three sides?", "a": "triangle", "reward": 50},
        {"q": "What is the capital of the United States?", "a": "washington dc", "reward": 50},
        {"q": "What ocean is on the east coast of the United States?", "a": "atlantic", "reward": 50},
        {"q": "How many hours are in a day?", "a": "24", "reward": 50},
        {"q": "What animal says 'meow'?", "a": "cat", "reward": 50},
        {"q": "What is 9 + 1?", "a": "10", "reward": 50},
        {"q": "What color is grass?", "a": "green", "reward": 50},
        {"q": "What is frozen water called?", "a": "ice", "reward": 50},
        {"q": "How many fingers are on one hand?", "a": "5", "reward": 50},
        {"q": "What is the capital of Canada?", "a": "ottawa", "reward": 50},
        {"q": "What do cows drink?", "a": "water", "reward": 50},
        {"q": "What is 5 x 5?", "a": "25", "reward": 50},
        {"q": "What is the color of snow?", "a": "white", "reward": 50},
        {"q": "What animal barks?", "a": "dog", "reward": 50},
        {"q": "How many wheels does a bicycle have?", "a": "2", "reward": 50},
        {"q": "What is the first letter of the alphabet?", "a": "a", "reward": 50},
        {"q": "What fruit is red and often associated with doctors?", "a": "apple", "reward": 50},
        {"q": "What is 2 + 2?", "a": "4", "reward": 50},
        {"q": "What is the capital of Spain?", "a": "madrid", "reward": 50},
    ],
    "medium": [
        {"q": "What is the chemical symbol for water?", "a": "h2o", "reward": 150},
        {"q": "What is the square root of 144?", "a": "12", "reward": 150},
        {"q": "Who painted the Mona Lisa?", "a": "da vinci", "reward": 150},
        {"q": "What is the smallest prime number?", "a": "2", "reward": 150},
        {"q": "What element has the symbol Au?", "a": "gold", "reward": 150},
        {"q": "What year did World War II end?", "a": "1945", "reward": 150},
        {"q": "How many players are on a basketball team on the court?", "a": "5", "reward": 150},
        {"q": "What is the largest ocean on Earth?", "a": "pacific", "reward": 150},
        {"q": "Who wrote 'Romeo and Juliet'?", "a": "shakespeare", "reward": 150},
        {"q": "What gas do plants absorb from the atmosphere?", "a": "carbon dioxide", "reward": 150},
        {"q": "What is the capital of Australia?", "a": "canberra", "reward": 150},
        {"q": "How many degrees are in a right angle?", "a": "90", "reward": 150},
        {"q": "What is the boiling point of water in celsius?", "a": "100", "reward": 150},
        {"q": "Who discovered gravity (falling apple story)?", "a": "newton", "reward": 150},
        {"q": "What is the hardest natural substance?", "a": "diamond", "reward": 150},
        {"q": "What is the capital of Germany?", "a": "berlin", "reward": 150},
        {"q": "What is 15 x 3?", "a": "45", "reward": 150},
        {"q": "Which planet has rings?", "a": "saturn", "reward": 150},
        {"q": "What language is primarily spoken in Brazil?", "a": "portuguese", "reward": 150},
        {"q": "How many bones are in an adult human hand?", "a": "27", "reward": 150},
        {"q": "What is the largest desert in the world?", "a": "antarctica", "reward": 150},
        {"q": "What organ pumps blood through the body?", "a": "heart", "reward": 150},
        {"q": "What is the capital of India?", "a": "new delhi", "reward": 150},
        {"q": "What is the freezing point of water in celsius?", "a": "0", "reward": 150},
        {"q": "Who wrote '1984'?", "a": "orwell", "reward": 150},
        {"q": "What is 100 divided by 4?", "a": "25", "reward": 150},
        {"q": "What is the main gas in Earth's atmosphere?", "a": "nitrogen", "reward": 150},
        {"q": "Which continent is Egypt in?", "a": "africa", "reward": 150},
        {"q": "How many strings does a standard guitar have?", "a": "6", "reward": 150},
        {"q": "What is the capital of Mexico?", "a": "mexico city", "reward": 150},
        {"q": "What does DNA stand for? (short answer)", "a": "deoxyribonucleic acid", "reward": 150},
        {"q": "What is 11 x 11?", "a": "121", "reward": 150},
        {"q": "What is the tallest mammal?", "a": "giraffe", "reward": 150},
    ],
    "hard": [
        {"q": "How many bones are in the human body?", "a": "206", "reward": 300},
        {"q": "What is the speed of light in km/s? (approximate)", "a": "300000", "reward": 300},
        {"q": "What is the atomic number of carbon?", "a": "6", "reward": 300},
        {"q": "In what year was the Eiffel Tower built?", "a": "1889", "reward": 300},
        {"q": "What is the longest river in the world?", "a": "nile", "reward": 300},
        {"q": "What is the chemical symbol for gold?", "a": "au", "reward": 300},
        {"q": "Who developed the theory of relativity?", "a": "einstein", "reward": 300},
        {"q": "What is the capital of Iceland?", "a": "reykjavik", "reward": 300},
        {"q": "What is the largest organ in the human body?", "a": "skin", "reward": 300},
        {"q": "What year did the Titanic sink?", "a": "1912", "reward": 300},
        {"q": "What is the smallest unit of matter?", "a": "atom", "reward": 300},
        {"q": "Who painted the ceiling of the Sistine Chapel?", "a": "michelangelo", "reward": 300},
        {"q": "What is the powerhouse of the cell?", "a": "mitochondria", "reward": 300},
        {"q": "What is the capital of South Korea?", "a": "seoul", "reward": 300},
        {"q": "What is 13 squared?", "a": "169", "reward": 300},
        {"q": "Which element has atomic number 1?", "a": "hydrogen", "reward": 300},
        {"q": "What is the longest bone in the human body?", "a": "femur", "reward": 300},
        {"q": "What is the largest island in the world?", "a": "greenland", "reward": 300},
        {"q": "What is the capital of Argentina?", "a": "buenos aires", "reward": 300},
        {"q": "Who wrote 'The Odyssey'?", "a": "homer", "reward": 300},
        {"q": "What is the square root of 225?", "a": "15", "reward": 300},
        {"q": "What is the chemical symbol for sodium?", "a": "na", "reward": 300},
        {"q": "How many elements are in the periodic table?", "a": "118", "reward": 300},
        {"q": "What is the capital of Norway?", "a": "oslo", "reward": 300},
        {"q": "What is 144 divided by 12?", "a": "12", "reward": 300},
        {"q": "Which planet is closest to the sun?", "a": "mercury", "reward": 300},
        {"q": "What is the study of earthquakes called?", "a": "seismology", "reward": 300},
        {"q": "Who discovered penicillin?", "a": "fleming", "reward": 300},
        {"q": "What is the capital of Turkey?", "a": "ankara", "reward": 300},
        {"q": "What is the freezing point of water in fahrenheit?", "a": "32", "reward": 300},
        {"q": "What is the tallest mountain in the world?", "a": "everest", "reward": 300},
    ],
}

class TriviaView(discord.ui.View):
    def __init__(self, user, question, difficulty):
        super().__init__(timeout=30)
        self.user = user; self.question = question; self.difficulty = difficulty; self.answered = False

    @discord.ui.button(label="💡 50/50 Lifeline", style=discord.ButtonStyle.grey)
    async def lifeline(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        button.disabled = True
        await interaction.response.edit_message(
            content=f"💡  **50/50 Lifeline used!** Hint: The answer starts with **'{self.question['a'][0].upper()}'**",
            view=self,
        )

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.blurple)
    async def skip(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        self.answered = True; self.stop()
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(
            embed=_base_embed("⏭️  Question Skipped", f"The answer was **{self.question['a']}**.\nNo money lost!", C.NEUTRAL),
            view=self,
        )

@tree.command(name="trivia", description="Answer trivia and win money!")
@app_commands.describe(difficulty="Choose difficulty: easy, medium, or hard")
@app_commands.choices(difficulty=[
    app_commands.Choice(name="🟢 Easy ($50)",    value="easy"),
    app_commands.Choice(name="🟡 Medium ($150)",  value="medium"),
    app_commands.Choice(name="🔴 Hard ($300)",    value="hard"),
])
async def trivia(interaction: discord.Interaction, difficulty: str = "easy"):
    q = random.choice(TRIVIA_QUESTIONS[difficulty])
    diff_colors  = {"easy": C.SUCCESS, "medium": C.WARNING, "hard": C.DANGER}
    diff_emojis  = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}

    view = TriviaView(interaction.user, q, difficulty)
    embed = _base_embed("❓  Trivia Time!", color=diff_colors[difficulty])
    embed.add_field(name="Question",    value=f"**{q['q']}**",                                   inline=False)
    embed.add_field(name="Difficulty",  value=f"{diff_emojis[difficulty]} {difficulty.capitalize()}", inline=True)
    embed.add_field(name="Reward",      value=f"**${q['reward']}**",                              inline=True)
    embed.add_field(name="Penalty",     value=f"**-${q['reward'] // 2}**",                        inline=True)
    embed.set_footer(text="Type your answer in chat! You have 30 seconds.")
    await interaction.response.send_message(embed=embed, view=view)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        if view.answered: return
        view.answered = True
        if msg.content.lower().strip() == q["a"]:
            new_bal = update_balance(interaction.user.id, q["reward"])
            result_embed = _base_embed(
                "✅  Correct!",
                f"The answer was **{q['a']}**!\n\n🎉  You earned **${q['reward']}**!\n💰  Balance: **${new_bal:,}**",
                C.SUCCESS,
            )
        else:
            penalty = q["reward"] // 2
            new_bal = update_balance(interaction.user.id, -penalty)
            result_embed = _base_embed(
                "❌  Wrong!",
                f"The correct answer was **{q['a']}**.\n\nYou lost **${penalty}**.\n💰  Balance: **${new_bal:,}**",
                C.DANGER,
            )
        for child in view.children: child.disabled = True
        view.stop()
        await interaction.edit_original_response(embed=result_embed, view=view)
    except asyncio.TimeoutError:
        if not view.answered:
            for child in view.children: child.disabled = True
            view.stop()
            await interaction.edit_original_response(
                embed=_base_embed("⏱️  Time's Up!", f"The answer was **{q['a']}**.\nNo penalty for timeout!", C.NEUTRAL),
                view=view,
            )


# ── 🃏 BLACKJACK ──────────────────────────────────────────────────────────────
def draw_card():
    return random.choice(["2","3","4","5","6","7","8","9","10","J","Q","K","A"])

def card_value(card):
    if card in ["J","Q","K"]: return 10
    elif card == "A": return 11
    return int(card)

def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces = hand.count("A")
    while total > 21 and aces:
        total -= 10; aces -= 1
    return total

def hand_str(hand):
    return " ".join(hand)

class BlackjackView(discord.ui.View):
    def __init__(self, user, bet, player, dealer):
        super().__init__(timeout=60)
        self.user = user; self.bet = bet; self.player = player; self.dealer = dealer; self.doubled = False

    def build_embed(self, show_dealer=False):
        embed = _base_embed("🃏  Blackjack", color=discord.Color.from_rgb(0, 120, 60))
        embed.add_field(name="Your Hand",    value=f"{hand_str(self.player)} — **Total: {hand_value(self.player)}**", inline=False)
        if show_dealer:
            embed.add_field(name="Dealer's Hand", value=f"{hand_str(self.dealer)} — **Total: {hand_value(self.dealer)}**", inline=False)
        else:
            embed.add_field(name="Dealer's Hand", value=f"{self.dealer[0]} ❓", inline=False)
        embed.add_field(name="💵 Bet",     value=f"**${self.bet:,}**",                    inline=True)
        embed.add_field(name="💰 Balance", value=f"**${get_balance(self.user.id):,}**",   inline=True)
        return embed

    async def end_game(self, interaction):
        while hand_value(self.dealer) < 17:
            self.dealer.append(draw_card())
        p = hand_value(self.player); d = hand_value(self.dealer)
        embed = self.build_embed(show_dealer=True)
        if d > 21 or p > d:
            new_bal = update_balance(self.user.id, self.bet)
            embed.add_field(name="🏆 Result", value=f"**You win! +${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = C.SUCCESS
        elif p == d:
            embed.add_field(name="🤝 Result", value=f"**Tie! Bet returned.**\nBalance: **${get_balance(self.user.id):,}**", inline=False)
            embed.color = C.WARNING
        else:
            new_bal = update_balance(self.user.id, -self.bet)
            embed.add_field(name="💔 Result", value=f"**Dealer wins! -${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = C.DANGER
        for child in self.children: child.disabled = True
        self.stop()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="👊 Hit",          style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        self.player.append(draw_card())
        pv = hand_value(self.player)
        if pv > 21:
            new_bal = update_balance(self.user.id, -self.bet)
            embed = self.build_embed()
            embed.add_field(name="💥 Bust!", value=f"You went over 21! Lost **${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = C.DANGER
            for child in self.children: child.disabled = True
            self.stop()
            await interaction.response.edit_message(embed=embed, view=self)
        elif pv == 21:
            await self.end_game(interaction)
        else:
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🛑 Stand",         style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        await self.end_game(interaction)

    @discord.ui.button(label="2️⃣ Double Down", style=discord.ButtonStyle.blurple)
    async def double_down(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        if get_balance(self.user.id) < self.bet:
            await interaction.response.send_message("❌ Not enough balance to double down!", ephemeral=True); return
        self.bet *= 2; self.player.append(draw_card()); button.disabled = True; self.doubled = True
        if hand_value(self.player) > 21:
            new_bal = update_balance(self.user.id, -self.bet)
            embed = self.build_embed()
            embed.add_field(name="💥 Bust!", value=f"Doubled and busted! Lost **${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = C.DANGER
            for child in self.children: child.disabled = True
            self.stop()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.end_game(interaction)

@tree.command(name="blackjack", description="Play Blackjack with Hit, Stand, and Double Down!")
@app_commands.describe(bet="Amount to bet (default: 10)")
async def blackjack(interaction: discord.Interaction, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Bet must be more than $0!", C.DANGER), ephemeral=True); return
    if bet > bal:
        await interaction.response.send_message(embed=_base_embed("❌ Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True); return
    player = [draw_card(), draw_card()]; dealer = [draw_card(), draw_card()]
    if hand_value(player) == 21:
        winnings = int(bet * 1.5)
        new_bal  = update_balance(interaction.user.id, winnings)
        embed = _base_embed("🃏  NATURAL BLACKJACK! 🎉", color=C.CASINO)
        embed.add_field(name="Your Hand", value=f"{hand_str(player)} — **21**",                         inline=False)
        embed.add_field(name="Result",    value=f"**Blackjack! You win ${winnings:,}!**\nBalance: **${new_bal:,}**", inline=False)
        await interaction.response.send_message(embed=embed); return
    view = BlackjackView(interaction.user, bet, player, dealer)
    embed = view.build_embed()
    embed.set_footer(text="Hit · Stand · Double Down")
    await interaction.response.send_message(embed=embed, view=view)


# ── 💣 MINESWEEPER ────────────────────────────────────────────────────────────
class MinesweeperView(discord.ui.View):
    def __init__(self, user, size, mines, bet):
        super().__init__(timeout=120)
        self.user = user; self.size = size; self.mines = mines; self.bet = bet
        self.revealed = 0; self.safe_cells = size * size - mines; self.game_over = False
        self.board = [[0] * size for _ in range(size)]
        self.mine_set = set(random.sample(range(size * size), mines))
        for pos in self.mine_set:
            self.board[pos // size][pos % size] = -1
        for r in range(size):
            for c in range(size):
                if self.board[r][c] == -1: continue
                self.board[r][c] = sum(
                    1 for dr in [-1,0,1] for dc in [-1,0,1]
                    if 0 <= r+dr < size and 0 <= c+dc < size and self.board[r+dr][c+dc] == -1
                )
        self.revealed_cells = set()
        self._add_buttons()

    def _add_buttons(self):
        for r in range(self.size):
            for c in range(self.size):
                pos = r * self.size + c
                btn = discord.ui.Button(label="?", row=r, style=discord.ButtonStyle.grey, custom_id=f"cell_{pos}")
                btn.callback = self.make_callback(r, c, pos)
                self.add_item(btn)

    def make_callback(self, r, c, pos):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
            if self.game_over or pos in self.revealed_cells:
                await interaction.response.send_message("❌ Already revealed!", ephemeral=True); return
            self.revealed_cells.add(pos)
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == f"cell_{pos}":
                    if pos in self.mine_set:
                        item.label = "💣"; item.style = discord.ButtonStyle.red; item.disabled = True
                    else:
                        val = self.board[r][c]
                        item.label = str(val) if val > 0 else "·"; item.style = discord.ButtonStyle.green; item.disabled = True
            if pos in self.mine_set:
                self.game_over = True
                new_bal = update_balance(self.user.id, -self.bet)
                for item in self.children: item.disabled = True
                self.stop()
                await interaction.response.edit_message(
                    embed=_base_embed("💣  BOOM! You hit a mine!", f"Revealed **{self.revealed}** safe cells before hitting a mine.\nLost **${self.bet:,}**!\nBalance: **${new_bal:,}**", C.DANGER),
                    view=self,
                )
            else:
                self.revealed += 1
                current_reward = int(self.bet * (self.revealed / self.safe_cells) * 2)
                if self.revealed == self.safe_cells:
                    self.game_over = True
                    new_bal = update_balance(self.user.id, self.bet * 3)
                    for item in self.children: item.disabled = True
                    self.stop()
                    await interaction.response.edit_message(
                        embed=_base_embed("💣  PERFECT CLEAR! 🎉", f"All **{self.safe_cells}** safe cells revealed!\nWon **${self.bet * 3:,}**!\nBalance: **${new_bal:,}**", C.CASINO),
                        view=self,
                    )
                else:
                    embed = _base_embed("💣  Minesweeper", color=C.PRIMARY)
                    embed.add_field(name="✅ Safe Cells Found",          value=f"**{self.revealed}/{self.safe_cells}**", inline=True)
                    embed.add_field(name="💰 Cashout Value",             value=f"**${current_reward:,}**",              inline=True)
                    embed.add_field(name="💵 Bet",                       value=f"**${self.bet:,}**",                    inline=True)
                    embed.set_footer(text="Keep going or cash out to secure your winnings!")
                    await interaction.response.edit_message(embed=embed, view=self)
        return callback

    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.green, row=4)
    async def cash_out(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True); return
        if self.revealed == 0:
            await interaction.response.send_message("❌ Reveal at least one cell before cashing out!", ephemeral=True); return
        reward  = int(self.bet * (self.revealed / self.safe_cells) * 2)
        new_bal = update_balance(self.user.id, reward)
        self.game_over = True
        for item in self.children: item.disabled = True
        self.stop()
        await interaction.response.edit_message(
            embed=_base_embed("💰  Cashed Out!", f"Revealed **{self.revealed}/{self.safe_cells}** safe cells!\nCashed out **${reward:,}**!\nBalance: **${new_bal:,}**", C.SUCCESS),
            view=self,
        )

@tree.command(name="minesweeper", description="Play interactive Minesweeper and cash out anytime!")
@app_commands.describe(size="Board size 3-5 (default: 4)", mines="Number of mines (default: 3)", bet="Amount to bet (default: 20)")
async def minesweeper(interaction: discord.Interaction, size: int = 4, mines: int = 3, bet: int = 20):
    bal = get_balance(interaction.user.id)
    if size < 3 or size > 5:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Size must be between 3 and 5!", C.DANGER), ephemeral=True); return
    if mines >= size * size - 1:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Too many mines!", C.DANGER), ephemeral=True); return
    if bet <= 0:
        await interaction.response.send_message(embed=_base_embed("❌ Error", "Bet must be more than $0!", C.DANGER), ephemeral=True); return
    if bet > bal:
        await interaction.response.send_message(embed=_base_embed("❌ Insufficient Funds", f"You only have **${bal:,}**!", C.DANGER), ephemeral=True); return

    view = MinesweeperView(interaction.user, size, mines, bet)
    embed = _base_embed("💣  Minesweeper", color=C.PRIMARY)
    embed.add_field(name="📐 Board",        value=f"**{size}x{size}**",           inline=True)
    embed.add_field(name="💣 Mines",        value=f"**{mines}**",                 inline=True)
    embed.add_field(name="✅ Safe Cells",   value=f"**{size*size - mines}**",     inline=True)
    embed.add_field(name="💵 Bet",          value=f"**${bet:,}**",                inline=True)
    embed.add_field(name="🏆 Full Clear",   value=f"**+${bet * 3:,}**",           inline=True)
    embed.add_field(name="Rules", value="Click cells to reveal them. Hit a mine and you lose!\nCash out anytime to keep partial winnings.", inline=False)
    embed.set_footer(text="Good luck! Click any cell to start.")
    await interaction.response.send_message(embed=embed, view=view)


# ══════════════════════════════════════════════════════════════════════════════
# 🛡️ ERROR HANDLING & STARTUP
# ══════════════════════════════════════════════════════════════════════════════
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=_base_embed("🚫  Permission Denied", "You don't have permission to use this command.", C.DANGER))
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(embed=_base_embed("❌  Error", str(error), C.DANGER))

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print("Bot ready.")

bot.run(BOT_TOKEN)
