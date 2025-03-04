from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import AudioPiped, StreamAudioEnded
import yt_dlp
import json
import os

# Import konfigurasi dari config.py
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, OWNER_ID

# Inisialisasi Bot & PyTgCalls untuk voice chat
bot = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
app = Client(SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
call = PyTgCalls(app)

# Dictionary untuk antrian lagu
music_queue = {}

# File penyimpanan data pengguna dan grup
DATA_FILE = "users_groups.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"users": [], "groups": []}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Fungsi untuk menangani perintah /start
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambahkan ke Grup", url="https://t.me/your_bot?startgroup=true")],
        [InlineKeyboardButton("❓ Bantuan dan Perintah", callback_data="help")]
    ])
    text = """\
🎵 **Music Bot**  
Bot pemutar musik di grup Telegram.

📌 **Gunakan /play [judul lagu] untuk mulai memutar musik!**
"""
    await message.reply_photo(
        photo="https://your_image_link.com/music_bot.jpg",
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

# Fungsi untuk broadcast pesan (hanya untuk OWNER_ID)
@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_command(client, message):
    if not message.reply_to_message:
        return await message.reply("❌ Balas pesan yang ingin dikirim sebagai broadcast!")

    broadcast_message = message.reply_to_message
    success, failed = 0, 0

    for user in data["users"]:
        try:
            await client.forward_messages(user, broadcast_message.chat.id, broadcast_message.message_id)
            success += 1
        except:
            failed += 1

    for group in data["groups"]:
        try:
            await client.forward_messages(group, broadcast_message.chat.id, broadcast_message.message_id)
            success += 1
        except:
            failed += 1

    await message.reply(f"✅ Broadcast selesai!\n✅ Berhasil: {success}\n❌ Gagal: {failed}")

# Jalankan bot
app.start()
bot.run()
idle()
