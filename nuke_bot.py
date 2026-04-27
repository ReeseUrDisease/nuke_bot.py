import discord
from discord.ext import commands
import asyncio
import os

# ── Config ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")
print(f"Token loaded: {BOT_TOKEN is not None}")
print(f"Token length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")

# Only users with these IDs can run nuke commands
AUTHORIZED_USER_IDS = [
    933543370935128204,
]

# ── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Auth Check ────────────────────────────────────────────────────────────────
def is_authorized(ctx):
    return (
        ctx.author.guild_permissions.administrator
        and (not AUTHORIZED_USER_IDS or ctx.author.id in AUTHORIZED_USER_IDS)
    )

# ── Helpers ───────────────────────────────────────────────────────────────────
async def confirm(ctx, action: str) -> bool:
    """Ask for confirmation before nuking."""
    embed = discord.Embed(
        title="⚠️ Confirm Nuke",
        description=f"Are you sure you want to **{action}**?\n\nType `yes` to confirm or `no` to cancel.",
        color=discord.Color.red(),
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        reply = await bot.wait_for("message", timeout=15.0, check=check)
        return reply.content.lower() == "yes"
    except asyncio.TimeoutError:
        await ctx.send("⏱️ Confirmation timed out. Nuke cancelled.")
        return False


async def send_result(ctx, results: list[str]):
    embed = discord.Embed(
        title="💥 Nuke Complete",
        description="\n".join(results),
        color=discord.Color.orange(),
    )
    await ctx.send(embed=embed)


# ── Commands ──────────────────────────────────────────────────────────────────

@bot.command(name="nuke_channels")
@commands.check(is_authorized)
async def nuke_channels(ctx):
    """Delete all channels in the server."""
    if not await confirm(ctx, "delete ALL channels"):
        return

    guild = ctx.guild
    count = 0
    for channel in guild.channels:
        try:
            await channel.delete(reason="Nuke: channels")
            count += 1
            await asyncio.sleep(0.5)  # avoid rate limits
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    # Try to recreate a general channel to report results
    try:
        new_ch = await guild.create_text_channel("general")
        await new_ch.send(f"💥 Nuke complete. Deleted **{count}** channels.")
    except Exception:
        pass


@bot.command(name="nuke_roles")
@commands.check(is_authorized)
async def nuke_roles(ctx):
    """Delete all non-managed, non-default roles."""
    if not await confirm(ctx, "delete all roles"):
        return

    guild = ctx.guild
    count = 0
    for role in guild.roles:
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: roles")
            count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass

    await send_result(ctx, [f"🗑️ Deleted **{count}** roles."])


@bot.command(name="nuke_channels_roles")
@commands.check(is_authorized)
async def nuke_channels_roles(ctx):
    """Delete all channels and roles."""
    if not await confirm(ctx, "delete all channels AND roles"):
        return

    guild = ctx.guild
    ch_count = role_count = 0

    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: channels+roles")
            ch_count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass

    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: channels+roles")
            role_count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass

    try:
        new_ch = await guild.create_text_channel("general")
        await new_ch.send(f"💥 Nuked **{ch_count}** channels and **{role_count}** roles.")
    except Exception:
        pass


@bot.command(name="nuke_kick")
@commands.check(is_authorized)
async def nuke_kick(ctx):
    """Delete all channels & roles, then kick all non-bot members."""
    if not await confirm(ctx, "delete channels, roles, AND kick all members"):
        return

    guild = ctx.guild
    ch_count = role_count = kick_count = 0

    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: kick")
            ch_count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass

    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: kick")
            role_count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async for member in guild.fetch_members(limit=None):
        if member == ctx.author or member.bot:
            continue
        try:
            await member.kick(reason="Nuke: kick all")
            kick_count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass

    try:
        new_ch = await guild.create_text_channel("general")
        await new_ch.send(
            f"💥 Nuked: **{ch_count}** channels, **{role_count}** roles, **{kick_count}** members kicked."
        )
    except Exception:
        pass


@bot.command(name="nuke_full")
@commands.check(is_authorized)
async def nuke_full(ctx):
    """Full reset: channels, roles, emojis, and kick members."""
    if not await confirm(ctx, "FULL RESET — channels, roles, emojis, and kick all members"):
        return

    guild = ctx.guild
    ch_count = role_count = kick_count = emoji_count = 0

    # Delete channels
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: full reset")
            ch_count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Delete roles
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: full reset")
            role_count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Delete emojis
    for emoji in list(guild.emojis):
        try:
            await emoji.delete(reason="Nuke: full reset")
            emoji_count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Kick members
    async for member in guild.fetch_members(limit=None):
        if member == ctx.author or member.bot:
            continue
        try:
            await member.kick(reason="Nuke: full reset")
            kick_count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass

    try:
        new_ch = await guild.create_text_channel("general")
        await new_ch.send(
            f"💥 **Full Nuke Complete**\n"
            f"🗑️ Channels: {ch_count}\n"
            f"🎭 Roles: {role_count}\n"
            f"😀 Emojis: {emoji_count}\n"
            f"👢 Members kicked: {kick_count}"
        )
    except Exception:
        pass


# ── Help command ──────────────────────────────────────────────────────────────
@bot.command(name="nuke_help")
async def nuke_help(ctx):
    embed = discord.Embed(title="💥 Nuke Bot Commands", color=discord.Color.red())
    embed.add_field(name="!nuke_channels", value="Delete all channels", inline=False)
    embed.add_field(name="!nuke_roles", value="Delete all non-default roles", inline=False)
    embed.add_field(name="!nuke_channels_roles", value="Delete all channels and roles", inline=False)
    embed.add_field(name="!nuke_kick", value="Delete channels, roles, and kick all members", inline=False)
    embed.add_field(name="!nuke_full", value="Full reset: channels, roles, emojis, kick members", inline=False)
    embed.set_footer(text="⚠️ Requires Administrator permission. All actions ask for confirmation.")
    await ctx.send(embed=embed)


# ── Error Handling ────────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(f"❌ Error: {error}")


# ── Ready ─────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print("Nuke bot ready.")


bot.run(BOT_TOKEN)
