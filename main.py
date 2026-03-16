import discord
from discord.ext import commands
import json
import os
from datetime import datetime

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
config_data = load_json(CONFIG_FILE, {"button_message_id": None})


def stars_view(count: int) -> str:
    return "⭐" * count


def average_rating(user_reviews):
    if not user_reviews:
        return 0
    total = sum(r["stars"] for r in user_reviews)
    return round(total / len(user_reviews), 2)


class ReviewModal(discord.ui.Modal, title="إرسال تقييم"):
    target_name = discord.ui.TextInput(
        label="اسم الشخص",
        placeholder="مثال: خالد",
        required=True,
        max_length=50
    )

    stars = discord.ui.TextInput(
        label="عدد النجوم من 1 إلى 5",
        placeholder="مثال: 5",
        required=True,
        max_length=1
    )

    comment = discord.ui.TextInput(
        label="كيف كان التعامل؟",
        placeholder="مثال: سريع ومحترم",
        required=True,
        max_length=120,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        global reviews_data

        try:
            stars_num = int(self.stars.value)
        except ValueError:
            await interaction.response.send_message("عدد النجوم لازم يكون رقم من 1 إلى 5", ephemeral=True)
            return

        if stars_num < 1 or stars_num > 5:
            await interaction.response.send_message("عدد النجوم لازم يكون من 1 إلى 5 فقط", ephemeral=True)
            return

        target = self.target_name.value.strip()
        comment_text = self.comment.value.strip()

        if not target:
            await interaction.response.send_message("اكتب اسم الشخص بشكل صحيح", ephemeral=True)
            return

        if target not in reviews_data:
            reviews_data[target] = {
                "reviews": []
            }

        review_entry = {
            "author_id": interaction.user.id,
            "author_name": str(interaction.user),
            "stars": stars_num,
            "comment": comment_text,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        reviews_data[target]["reviews"].append(review_entry)
        save_json(REVIEWS_FILE, reviews_data)

        user_reviews = reviews_data[target]["reviews"]
        avg = average_rating(user_reviews)
        total_reviews = len(user_reviews)

        embed = discord.Embed(
            title="⭐ تقييم جديد ⭐",
            description=(
                f"## **تعامل ممتاز**\n\n"
                f"**الشخص:** {target}\n"
                f"**التقييم:** {stars_view(stars_num)} `({stars_num}/5)`\n"
                f"**الرأي:** {comment_text}\n"
                f"**المتوسط:** {avg} من 5\n"
                f"**عدد التقييمات:** {total_reviews}\n"
                f"**من:** {interaction.user.mention}"
            ),
            color=discord.Color.gold()
        )

        channel = bot.get_channel(REVIEW_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("ما لقيت روم التقييمات", ephemeral=True)
            return

        await channel.send(embed=embed)
        await interaction.response.send_message("تم إرسال تقييمك", ephemeral=True)


class ReviewButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⭐ قيّم", style=discord.ButtonStyle.success, custom_id="review_button")
    async def review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal())


async def ensure_button_message():
    global config_data

    channel = bot.get_channel(REVIEW_CHANNEL_ID)
    if channel is None:
        print("❌ ما لقيت روم التقييمات")
        return

    old_message_id = config_data.get("button_message_id")

    if old_message_id:
        try:
            old_message = await channel.fetch_message(old_message_id)
            if old_message:
                return
        except Exception:
            pass

    msg = await channel.send(
        content="**اضغط الزر تحت للتقييم**",
        view=ReviewButtonView()
    )

    config_data["button_message_id"] = msg.id
    save_json(CONFIG_FILE, config_data)
    print("✅ تم إرسال زر التقييم")


@bot.event
async def on_ready():
    bot.add_view(ReviewButtonView())
    print(f"✅ تم تشغيل البوت: {bot.user}")
    await ensure_button_message()


bot.run(TOKEN)
