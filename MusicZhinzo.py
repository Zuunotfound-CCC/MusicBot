from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import StreamAudioEnded
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp
import json
import os

# Import konfigurasi dari config.py
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, OWNER_ID

# Data channel dan grup yang harus diikuti
REQUIRED_CHANNEL = "@your_channel"
REQUIRED_GROUP = "@your_group"

# Inisialisasi Bot & PyTgCalls untuk voice chat
bot = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
app = Client(SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
call = PyTgCalls(app)

# Dictionary untuk antrian lagu
music_queue = {}

# File penyimpanan data pengguna dan grup
DATA_FILE = "users_groups.json"

# Load data dari file
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"users": [], "groups": []}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Fungsi untuk mengecek apakah user sudah join
async def is_member(user_id):
    try:
        chat_member_channel = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        chat_member_group = await bot.get_chat_member(REQUIRED_GROUP, user_id)
        return chat_member_channel.status in ["member", "administrator", "creator"] and chat_member_group.status in ["member", "administrator", "creator"]
    except:
        return False

# Middleware untuk cek join sebelum akses bot
@bot.on_message(filters.command(["start", "play", "pause", "resume", "stop", "queue", "help"]))
async def check_join(client, message):
    user_id = message.from_user.id
    if not await is_member(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton("💬 Join Group", url=f"https://t.me/{REQUIRED_GROUP[1:]}")],
            [InlineKeyboardButton("✅ Sudah Join", callback_data="check_join")]
        ])
        return await message.reply("🔹 **Silakan bergabung ke Channel & Grup untuk menggunakan bot ini!**", reply_markup=keyboard)

# Fungsi untuk menangani perintah /start
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambahkan ke Grup", url="https://t.me/your_bot?startgroup=true")],
        [InlineKeyboardButton("❓ Bantuan dan Perintah", callback_data="help")]
    ])
    text = """\
🎵 **Apple Music**  
Saya **Apple Music**, bot pemutar musik Telegram.  

📌 **Gunakan /play [judul lagu] untuk mulai memutar musik!**
"""
    await message.reply_photo(
        photo="https://your_image_link.com/apple_music.jpg",
        caption=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Fungsi untuk mencari lagu di YouTube
async def search_youtube(query):
    ydl_opts = {'format': 'bestaudio'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        return {"title": info['title'], "url": info['url']}

# Fungsi untuk memutar lagu
@bot.on_message(filters.command("play"))
async def play(_, message):
    chat_id = message.chat.id
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("Gunakan: **/play [judul lagu]**")

    song = await search_youtube(query)

    if chat_id not in music_queue:
        music_queue[chat_id] = []

    if call.active_calls.get(chat_id):
        music_queue[chat_id].append(song)
        return await message.reply(f"🎶 **Ditambahkan ke antrian:** {song['title']}")

    await call.join_group_call(chat_id, AudioPiped(song['url']))
    await message.reply(f"🎶 **Memutar:** {song['title']}")

# Fungsi untuk menangani saat lagu selesai diputar
@call.on_stream_end()
async def on_stream_end(client, update: StreamAudioEnded):
    chat_id = update.chat_id
    if chat_id in music_queue and music_queue[chat_id]:
        next_song = music_queue[chat_id].pop(0)
        await call.join_group_call(chat_id, AudioPiped(next_song['url']))
        await bot.send_message(chat_id, f"🎶 **Memutar lagu berikutnya:** {next_song['title']}")
    else:
        await call.leave_group_call(chat_id)

# Fungsi untuk pause musik
@bot.on_message(filters.command("pause"))
async def pause(_, message):
    chat_id = message.chat.id
    if call.active_calls.get(chat_id):
        await call.pause_stream(chat_id)
        await message.reply("⏸ **Musik dijeda.**")

# Fungsi untuk resume musik
@bot.on_message(filters.command("resume"))
async def resume(_, message):
    chat_id = message.chat.id
    if call.active_calls.get(chat_id):
        await call.resume_stream(chat_id)
        await message.reply("▶️ **Melanjutkan musik.**")

# Fungsi untuk stop musik
@bot.on_message(filters.command("stop"))
async def stop(_, message):
    chat_id = message.chat.id
    await call.leave_group_call(chat_id)
    await message.reply("⏹ **Musik dihentikan.**")

# Fungsi untuk melihat antrian lagu
@bot.on_message(filters.command("queue"))
async def queue_command(_, message):
    chat_id = message.chat.id
    if chat_id in music_queue and music_queue[chat_id]:
        queue_text = "\n".join([f"🎵 {i+1}. {song['title']}" for i, song in enumerate(music_queue[chat_id])])
        await message.reply(f"📜 **Antrian Lagu:**\n{queue_text}")
    else:
        await message.reply("📭 **Antrian kosong.**")

# Fungsi untuk menampilkan daftar perintah
@bot.on_message(filters.command("help"))
async def help_command(client, message):
    text = """\
**🎵 Daftar Perintah Music Bot 🎵**

**🎶 Pemutar Musik:**
- `/play [judul]` → Memutar musik dari YouTube
- `/pause` → Menjeda musik yang sedang diputar
- `/resume` → Melanjutkan musik yang dijeda
- `/stop` → Menghentikan pemutaran musik
- `/queue` → Melihat daftar antrian lagu

**🔍 Cek Informasi:**
- Tekan tombol di bawah untuk mengecek ID Anda atau ID Grup.
"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Cek ID Pengguna", callback_data="check_user_id"),
         InlineKeyboardButton("🔎 Cek ID Grup", callback_data="check_group_id")]
    ])
    await message.reply(text, reply_markup=keyboard, parse_mode="Markdown")

# Fungsi untuk menangani tombol "Cek ID Pengguna"
@bot.on_callback_query(filters.regex("check_user_id"))
async def check_user_id_callback(client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer(f"🆔 ID Pengguna Anda: {user_id}", show_alert=True)

# Fungsi untuk menangani tombol "Cek ID Grup"
@bot.on_callback_query(filters.regex("check_group_id"))
async def check_group_id_callback(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.answer(f"🆔 ID Grup Ini: {chat_id}", show_alert=True)

# Jalankan bot
app.start()
bot.run()
