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
config_data = load_json(CONFIG_FILE, {"panel_message_id": None})


def stars_view(count: int) -> str:
    return "⭐" * count


def average_rating(user_reviews):
    if not user_reviews:
        return 0
    total = sum(r["stars"] for r in user_reviews)
    return round(total / len(user_reviews), 2)


class ReviewModal(discord.ui.Modal, title="إرسال تقييم"):
    target_name = discord.ui.TextInput(
        label="اسم الشخص أو البائع",
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
            await interaction.response.send_message("عدد النجوم لازم يكون رقم من 1 إلى 5.", ephemeral=True)
            return

        if stars_num < 1 or stars_num > 5:
            await interaction.response.send_message("عدد النجوم لازم يكون من 1 إلى 5 فقط.", ephemeral=True)
            return

        target = self.target_name.value.strip()
        if not target:
            await interaction.response.send_message("اكتب اسم الشخص بشكل صحيح.", ephemeral=True)
            return

        if target not in reviews_data:
            reviews_data[target] = {
                "reviews": []
            }

        review_entry = {
            "author_id": interaction.user.id,
            "author_name": str(interaction.user),
            "stars": stars_num,
            "comment": self.comment.value.strip(),
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
                f"# **تعامل ممتاز**\n"
                f"## **{self.comment.value.strip()}**\n\n"
                f"**الشخص:** {target}\n"
                f"**التقييم:** {stars_view(stars_num)} `({stars_num}/5)`\n"
                f"**المتوسط:** {avg} من 5\n"
                f"**عدد التقييمات:** {total_reviews}\n"
                f"**من:** {interaction.user.mention}"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="نظام تقييم المتجر")

        channel = bot.get_channel(REVIEW_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("ما لقيت روم التقييمات.", ephemeral=True)
            return

        await channel.send(embed=embed)
        await interaction.response.send_message("تم إرسال التقييم وحفظه.", ephemeral=True)


class ReviewPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⭐ قيّم", style=discord.ButtonStyle.success, custom_id="persistent_review_button")
    async def review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal())


async def ensure_panel_message():
    global config_data

    channel = bot.get_channel(REVIEW_CHANNEL_ID)
    if channel is None:
        print("❌ ما لقيت روم التقييمات")
        return

    panel_message_id = config_data.get("panel_message_id")

    if panel_message_id:
        try:
            msg = await channel.fetch_message(panel_message_id)
            if msg:
                return
        except Exception:
            pass

    embed = discord.Embed(
        title="⭐ نظام التقييم",
        description=(
            "# **قيّم التعامل**\n"
            "## **اضغط الزر تحت وأرسل تقييمك**\n\n"
            "**التقييم يظهر بالنجوم ويحفظ تلقائيًا.**"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="لوحة التقييم الثابتة")

    msg = await channel.send(embed=embed, view=ReviewPanelView())
    config_data["panel_message_id"] = msg.id
    save_json(CONFIG_FILE, config_data)
    print("✅ تم إنشاء لوحة التقييم")


@bot.event
async def on_ready():
    bot.add_view(ReviewPanelView())
    print(f"✅ تم تشغيل البوت: {bot.user}")
    await ensure_panel_message()


@bot.command(name="سمعة")
async def reputation(ctx, *, target: str = None):
    if not target:
        await ctx.reply("اكتب كذا: `!سمعة خالد`")
        return

    if target not in reviews_data or not reviews_data[target]["reviews"]:
        await ctx.reply("هذا الشخص ما عنده تقييمات إلى الآن.")
        return

    user_reviews = reviews_data[target]["reviews"]
    avg = average_rating(user_reviews)
    total_reviews = len(user_reviews)
    rounded_stars = max(1, min(5, round(avg)))

    embed = discord.Embed(
        title="📊 سمعة",
        description=(
            f"**الاسم:** {target}\n"
            f"**المتوسط:** {avg} من 5\n"
            f"**النجوم:** {stars_view(rounded_stars)}\n"
            f"**عدد التقييمات:** {total_reviews}"
        ),
        color=discord.Color.blue()
    )

    latest_reviews = user_reviews[-5:][::-1]
    for i, review in enumerate(latest_reviews, start=1):
        embed.add_field(
            name=f"تقييم #{i} - {stars_view(review['stars'])}",
            value=f"**{review['comment']}**\nمن: <@{review['author_id']}>",
            inline=False
        )

    await ctx.reply(embed=embed)


bot.run(TOKEN)
