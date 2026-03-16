import discord
from discord.ext import commands
import json
import os
import time
from datetime import datetime, timezone

TOKEN = os.getenv("TOKEN")
REVIEW_CHANNEL_ID = 1482899764407435394

DATA_DIR = "/app/data"
REVIEWS_FILE = f"{DATA_DIR}/reviews.json"
CONFIG_FILE = f"{DATA_DIR}/config.json"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# pending_reviews[user_id] = {
#   "stars": 5,
#   "created_at": 1234567890,
#   "channel_id": 123
# }
pending_reviews = {}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path, default):
    ensure_data_dir()
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


reviews_data = load_json(REVIEWS_FILE, {})
config_data = load_json(CONFIG_FILE, {"message_id": None})


def stars_view(count: int) -> str:
    return "⭐" * count


def add_review(user: discord.Member | discord.User, stars: int, comment: str):
    user_id = str(user.id)

    if user_id not in reviews_data:
        reviews_data[user_id] = []

    reviews_data[user_id].append({
        "user_id": user.id,
        "user_name": str(user),
        "stars": stars,
        "comment": comment,
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    })

    save_json(REVIEWS_FILE, reviews_data)


def average_rating(user_id: int):
    user_reviews = reviews_data.get(str(user_id), [])
    if not user_reviews:
        return 0
    total = sum(item["stars"] for item in user_reviews)
    return round(total / len(user_reviews), 2)


def total_reviews(user_id: int):
    return len(reviews_data.get(str(user_id), []))


def build_review_embed(user: discord.Member | discord.User, stars: int, comment: str):
    avg = average_rating(user.id)
    total = total_reviews(user.id)

    embed = discord.Embed(
        title="⭐ تقييم جديد ⭐",
        description=(
            f"## **تقييم المتجر**\n\n"
            f"**العميل:** {user.mention}\n"
            f"**التقييم:** {stars_view(stars)} `({stars}/5)`\n"
            f"**عدد مرات التقييم:** {total}\n"
            f"**المتوسط:** {avg} من 5\n"
            f"**التجربة:** {comment}"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="شكرًا لك على تقييم المتجر")
    return embed


def cleanup_pending():
    now = time.time()
    expired_users = []

    for user_id, data in pending_reviews.items():
        if now - data["created_at"] > 180:
            expired_users.append(user_id)

    for user_id in expired_users:
        del pending_reviews[user_id]


class ReviewStarsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_click(self, interaction: discord.Interaction, stars: int):
        cleanup_pending()

        pending_reviews[interaction.user.id] = {
            "stars": stars,
            "created_at": time.time(),
            "channel_id": interaction.channel.id
        }

        await interaction.response.send_message(
            f"تم اختيار تقييمك: {stars_view(stars)}\n"
            f"**اكتب كلام حلو أو حدثنا عن تجربتك**\n"
            f"ولو ما تبي تكتب، اكتب `تخطي`.",
            ephemeral=True
        )

    @discord.ui.button(label="⭐ 1", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def rate_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, 1)

    @discord.ui.button(label="⭐ 2", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def rate_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, 2)

    @discord.ui.button(label="⭐ 3", style=discord.ButtonStyle.primary, custom_id="rate_3")
    async def rate_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, 3)

    @discord.ui.button(label="⭐ 4", style=discord.ButtonStyle.success, custom_id="rate_4")
    async def rate_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, 4)

    @discord.ui.button(label="⭐ 5", style=discord.ButtonStyle.success, custom_id="rate_5")
    async def rate_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, 5)


async def ensure_review_message():
    channel = bot.get_channel(REVIEW_CHANNEL_ID)
    if channel is None:
        print("❌ ما لقيت روم التقييم")
        return

    old_message_id = config_data.get("message_id")

    if old_message_id:
        try:
            msg = await channel.fetch_message(old_message_id)
            if msg:
                return
        except Exception:
            pass

    embed = discord.Embed(
        title="⭐ قيّم المتجر",
        description=(
            "## **رأيك يهمنا**\n\n"
            "**إذا أعجبك التعامل قيّمنا من 1 إلى 5 نجوم**\n"
            "**وبعد اختيار النجمة اكتب كلام حلو أو حدثنا عن تجربتك**"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="اضغط النجمة المناسبة")

    msg = await channel.send(embed=embed, view=ReviewStarsView())
    config_data["message_id"] = msg.id
    save_json(CONFIG_FILE, config_data)
    print("✅ تم إرسال رسالة التقييم")


@bot.event
async def on_ready():
    bot.add_view(ReviewStarsView())
    print(f"✅ تم تشغيل البوت: {bot.user}")
    await ensure_review_message()


@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    if message.channel.id != REVIEW_CHANNEL_ID:
        return

    cleanup_pending()

    pending = pending_reviews.get(message.author.id)
    if not pending:
        return

    if pending["channel_id"] != message.channel.id:
        return

    stars = pending["stars"]
    user_text = message.content.strip()

    if not user_text:
        return

    if user_text.lower() == "تخطي":
        user_text = "تعامل ممتاز"

    try:
        await message.delete()
    except Exception:
        pass

    add_review(message.author, stars, user_text)
    embed = build_review_embed(message.author, stars, user_text)
    await message.channel.send(embed=embed)

    del pending_reviews[message.author.id]


bot.run(TOKEN)
