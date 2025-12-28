import os
import subprocess
from pyrogram import Client, filters
from pymongo import MongoClient

# ===== ENV VARIABLES =====
API_ID = int(os.environ["27166502"])
API_HASH = os.environ["35b9c34a2b29b20bdae81d82e2863cec"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["7012709838"])
MONGO_URI = os.environ["mongodb+srv://adarshrajputx:CxjiTK56oacjwg78@cluster0.72l1y2f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"]
LOG_CHANNEL_ID = int(os.environ["-1003454021940"])  # private channel id

# ===== MONGO SETUP =====
mongo = MongoClient(MONGO_URI)
db = mongo["tg_stream_bot"]
admins_col = db["admins"]

# ===== BOT STATE =====
busy = False

def is_admin(uid: int) -> bool:
    if uid == OWNER_ID:
        return True
    return admins_col.find_one({"user_id": uid}) is not None

# ===== PYROGRAM CLIENT =====
app = Client(
    "tg_stream_pro",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ===== COMMANDS =====
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("🤖 TG Nudixfun Stream Bot\nAdmins only.")

@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin(client, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a user to add admin")

    uid = message.reply_to_message.from_user.id
    admins_col.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )
    await message.reply(f"✅ `{uid}` added as admin")

@app.on_message(filters.command("deladmin") & filters.user(OWNER_ID))
async def del_admin(client, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a user to remove admin")

    uid = message.reply_to_message.from_user.id
    admins_col.delete_one({"user_id": uid})
    await message.reply(f"❌ `{uid}` removed from admin")

@app.on_message(filters.command("admins"))
async def list_admins(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Not authorized")

    text = "👮 **Admin List**\n\n"
    for a in admins_col.find():
        text += f"• `{a['user_id']}`\n"
    await message.reply(text)

# ===== VIDEO HANDLER =====
@app.on_message(filters.video)
async def handle_video(client, message):
    global busy

    if not is_admin(message.from_user.id):
        return await message.reply("⛔ You are not authorized")

    if busy:
        return await message.reply("⏳ One video is processing, wait...")

    busy = True
    status = await message.reply("💧 Adding moving watermark...")

    input_video = await message.download()
    output_video = "stream.mp4"

    # Moving watermark FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf",
        "drawtext=text='TG Nudixfun':fontcolor=white@0.6:fontsize=28:"
        "x=mod(t*60\\,W-tw):y=H-th-20",
        "-c:a", "copy",
        output_video
    ]

    subprocess.run(cmd)

    await status.edit("📤 Saving to private channel...")

    # Upload to private channel first
    saved = await client.send_video(
        chat_id=LOG_CHANNEL_ID,
        video=output_video,
        supports_streaming=True,
        protect_content=True,
        caption="TG Nudixfun | Archive"
    )

    await status.edit("📨 Sending to admin...")

    # Forward same video to admin/user
    await saved.copy(
        chat_id=message.chat.id,
        caption="▶️ TG Nudixfun | Stream Ready",
        protect_content=True
    )

    # Cleanup
    os.remove(input_video)
    os.remove(output_video)
    await status.delete()
    busy = False

# ===== RUN =====
app.run()
