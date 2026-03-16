import discord
from discord.ext import commands
import json
import os

TOKEN = os.getenv("TOKEN")
REVIEW_CHANNEL_ID = 1482899764407435394
DATA_FILE = "reviews.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

if os.path.exists(DATA_FILE):
    with open(DATA_FILE) as f:
        reviews = json.load(f)
else:
    reviews = {}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(reviews, f, indent=4)

def stars(n):
    return "⭐" * n

# ===== زر التقييم =====

class ReviewButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⭐ قيّم", style=discord.ButtonStyle.green, custom_id="review_button")
    async def review(self, interaction: discord.Interaction, button: discord.ui.Button):

        modal = ReviewModal()
        await interaction.response.send_modal(modal)

# ===== فورم التقييم =====

class ReviewModal(discord.ui.Modal, title="إرسال تقييم"):

    user = discord.ui.TextInput(
        label="من تريد تقييمه",
        placeholder="اكتب اسم الشخص",
        required=True
    )

    stars_input = discord.ui.TextInput(
        label="عدد النجوم (1-5)",
        placeholder="مثال: 5",
        required=True
    )

    comment = discord.ui.TextInput(
        label="كيف كان التعامل؟",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            star_num = int(self.stars_input.value)
        except:
            await interaction.response.send_message("النجوم لازم رقم", ephemeral=True)
            return

        if star_num < 1 or star_num > 5:
            await interaction.response.send_message("النجوم من 1 إلى 5 فقط", ephemeral=True)
            return

        if self.user.value not in reviews:
            reviews[self.user.value] = []

        reviews[self.user.value].append(star_num)
        save()

        avg = sum(reviews[self.user.value]) / len(reviews[self.user.value])

        embed = discord.Embed(
            title="⭐ تقييم جديد ⭐",
            description=f"""
# تعامل ممتاز

**الشخص:** {self.user.value}

**التقييم:** {stars(star_num)}

**المتوسط:** {round(avg,2)}

**عدد التقييمات:** {len(reviews[self.user.value])}

**الرأي:**
{self.comment.value}
""",
            color=0xffd700
        )

        channel = bot.get_channel(REVIEW_CHANNEL_ID)
        await channel.send(embed=embed)

        await interaction.response.send_message("تم إرسال التقييم ✅", ephemeral=True)

# ===== تشغيل البوت =====

@bot.event
async def on_ready():
    print("البوت شغال")

    bot.add_view(ReviewButton())

    channel = bot.get_channel(REVIEW_CHANNEL_ID)

    embed = discord.Embed(
        title="⭐ نظام التقييم",
        description="""
اضغط الزر تحت لتقييم التعامل.

التقييم يظهر بالنجوم ⭐
""",
        color=0x00ff00
    )

    await channel.send(embed=embed, view=ReviewButton())

bot.run(TOKEN)
