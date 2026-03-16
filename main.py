import discord
from discord.ext import commands
import json
import os
from datetime import datetime

TOKEN = "حط_توكن_البوت_هنا"
REVIEW_CHANNEL_ID = 1482899764407435394
DATA_FILE = "/app/data/reviews.json"   # مهم عشان نحفظه على Volume
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def ensure_data_dir():
    os.makedirs("/app/data", exist_ok=True)

def load_reviews():
    ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_reviews(data):
    ensure_data_dir()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def stars_view(count: int) -> str:
    return "⭐" * count

def average_rating(user_reviews):
    if not user_reviews:
        return 0
    total = sum(r["stars"] for r in user_reviews)
    return round(total / len(user_reviews), 2)

reviews_data = load_reviews()

@bot.event
async def on_ready():
    print(f"✅ تم تشغيل البوت: {bot.user}")

@bot.command(name="قيم")
async def rate_user(ctx, member: discord.Member = None, stars: int = None, *, comment: str = None):
    global reviews_data

    if ctx.author.bot:
        return

    if member is None or stars is None or comment is None:
        embed = discord.Embed(
            title="⭐ طريقة التقييم",
            description="**اكتب:** `!قيم @الشخص عدد_النجوم الكلام`\n\n**مثال:** `!قيم @KHALID 5 ممتاز وسريع`",
            color=discord.Color.orange()
        )
        await ctx.reply(embed=embed)
        return

    if member.id == ctx.author.id:
        await ctx.reply("ما تقدر تقيم نفسك.")
        return

    if stars < 1 or stars > 5:
        await ctx.reply("عدد النجوم لازم يكون من 1 إلى 5 فقط.")
        return

    review_channel = bot.get_channel(REVIEW_CHANNEL_ID)
    if review_channel is None:
        await ctx.reply("ما لقيت روم التقييمات، تأكد من الآيدي والصلاحيات.")
        return

    target_id = str(member.id)

    if target_id not in reviews_data:
        reviews_data[target_id] = {
            "user_name": str(member),
            "reviews": []
        }

    review_entry = {
        "author_id": ctx.author.id,
        "author_name": str(ctx.author),
        "stars": stars,
        "comment": comment,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    reviews_data[target_id]["user_name"] = str(member)
    reviews_data[target_id]["reviews"].append(review_entry)
    save_reviews(reviews_data)

    user_reviews = reviews_data[target_id]["reviews"]
    avg = average_rating(user_reviews)
    total_reviews = len(user_reviews)

    embed = discord.Embed(
        title="⭐ تقييم جديد ⭐",
        description=(
            f"# **تعامل ممتاز**\n"
            f"## **{comment[:80]}**\n\n"
            f"**الشخص:** {member.mention}\n"
            f"**التقييم:** {stars_view(stars)} `({stars}/5)`\n"
            f"**المتوسط:** {avg} من 5\n"
            f"**عدد التقييمات:** {total_reviews}\n"
            f"**من:** {ctx.author.mention}"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="نظام تقييم المتجر")
    await review_channel.send(embed=embed)
    await ctx.reply("تم إرسال التقييم وحفظه.")

@bot.command(name="سمعة")
async def reputation(ctx, member: discord.Member = None):
    if member is None:
        await ctx.reply("اكتب الأمر كذا: `!سمعة @الشخص`")
        return

    target_id = str(member.id)

    if target_id not in reviews_data or not reviews_data[target_id]["reviews"]:
        await ctx.reply("هذا الشخص ما عنده تقييمات إلى الآن.")
        return

    user_reviews = reviews_data[target_id]["reviews"]
    avg = average_rating(user_reviews)
    total_reviews = len(user_reviews)

    rounded_stars = max(1, min(5, round(avg)))

    embed = discord.Embed(
        title="📊 سمعة العضو",
        description=(
            f"**الشخص:** {member.mention}\n"
            f"**المتوسط:** {avg} من 5\n"
            f"**النجوم:** {stars_view(rounded_stars)}\n"
            f"**عدد التقييمات:** {total_reviews}"
        ),
        color=discord.Color.green()
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
