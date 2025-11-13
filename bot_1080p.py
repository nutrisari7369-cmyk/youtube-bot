#!/usr/bin/env python3
import logging
import os
import asyncio
import tempfile
from pathlib import Path
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ✅ TOKEN VALID
BOT_TOKEN = "8382198132:AAEQ2Cm_C0kAqHPh6H_JqKOVrsTPcVoKIw8"

# Bot info
BOT_NAME = "YT Downloader Pro"
BOT_USERNAME = "@xxYTxDWNLDRxx_bot"

# Temporary directory
TMP_DIR = Path(tempfile.gettempdir()) / "yt_bot"
TMP_DIR.mkdir(exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🎬 **{BOT_NAME}**\n\n"
        f"Username: {BOT_USERNAME}\n\n"
        "Kirim link YouTube untuk download video/audio!\n\n"
        "⚡ **Fitur Premium:**\n"
        "• Download video (360p, 720p, 1080p)\n"
        "• Download audio MP3 kualitas tinggi\n"
        "• Support resolusi maksimal 1080p\n"
        "• Mudah dan cepat"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 **Cara penggunaan:**\n\n"
        "1. Kirim link YouTube\n"
        "2. Pilih format dan resolusi\n"
        "3. Tunggu proses download\n"
        "4. File akan dikirim otomatis\n\n"
        "📝 **Contoh link:**\n"
        "• https://www.youtube.com/watch?v=...\n"
        "• https://youtu.be/...\n\n"
        "🎯 **Resolusi tersedia:**\n"
        "• 360p (Standard)\n"
        "• 720p (HD)\n"
        "• 1080p (Full HD)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Check if it's a YouTube URL
    if any(domain in text for domain in ["youtube.com", "youtu.be"]):
        # Show format selection buttons
        keyboard = [
            [
                InlineKeyboardButton("🎥 360p", callback_data=f"360|{text}"),
                InlineKeyboardButton("🎥 720p", callback_data=f"720|{text}"),
            ],
            [
                InlineKeyboardButton("🎥 1080p", callback_data=f"1080|{text}"),
                InlineKeyboardButton("🎵 MP3 Audio", callback_data=f"audio|{text}"),
            ]
        ]
        
        await update.message.reply_text(
            "📹 **Pilih format dan resolusi:**\n\n"
            "• 360p - Kualitas standar, file kecil\n"
            "• 720p - HD, kualitas baik\n"
            "• 1080p - Full HD, kualitas terbaik\n"
            "• MP3 - Audio saja, kualitas tinggi",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            "❌ **Link tidak valid!**\n\n"
            "Kirim link YouTube yang valid.\n"
            "Contoh:\n"
            "• https://www.youtube.com/watch?v=...\n"
            "• https://youtu.be/..."
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        quality, url = data.split("|", 1)
        await process_download(query, quality, url)
    except Exception as e:
        await query.edit_message_text("❌ Terjadi error. Silakan coba lagi.")

async def process_download(query, quality, url):
    try:
        message = await query.edit_message_text("⏳ **Sedang memproses...**")
        
        # Download options dengan support 1080p
        ydl_opts = {
            'outtmpl': str(TMP_DIR / '%(id)s.%(ext)s'),
            'quiet': False,
        }
        
        if quality == 'audio':
            # MP3 dengan konversi FFmpeg
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            format_name = "MP3 Audio"
            file_extension = ".mp3"
        else:
            # Video download dengan support hingga 1080p
            # Gunakan format yang lebih baik untuk kualitas tinggi
            if quality == '1080':
                ydl_opts.update({
                    'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                    'merge_output_format': 'mp4',
                })
                format_name = "1080p Full HD"
            elif quality == '720':
                ydl_opts.update({
                    'format': 'best[height<=720]/best',
                })
                format_name = "720p HD"
            else:  # 360
                ydl_opts.update({
                    'format': 'best[height<=360]/best',
                })
                format_name = "360p Standard"
            
            file_extension = ".mp4"
        
        # Download file
        await message.edit_text(f"📥 **Mengunduh {format_name}...**")
        
        loop = asyncio.get_event_loop()
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, url, True)
            filename = ydl.prepare_filename(info)
        
        # Get final file path
        final_path = filename.rsplit('.', 1)[0] + file_extension
        
        # Check if file exists
        if not os.path.exists(final_path):
            # Try the original filename
            if os.path.exists(filename):
                final_path = filename
            else:
                await message.edit_text("❌ File tidak ditemukan setelah download!")
                return
        
        # Check file size (Telegram limit: 50MB for bots)
        file_size = os.path.getsize(final_path)
        file_size_mb = file_size // 1024 // 1024
        
        if file_size > 50 * 1024 * 1024:
            await message.edit_text(
                f"❌ File terlalu besar ({file_size_mb}MB).\n"
                f"Telegram batas 50MB untuk bot.\n\n"
                f"💡 Coba resolusi lebih rendah (720p atau 360p)."
            )
            try:
                os.remove(final_path)
            except:
                pass
            return
        
        # Send file
        await message.edit_text(f"📤 **Mengirim file {file_size_mb}MB...**")
        
        try:
            if quality == 'audio':
                await query.message.reply_audio(
                    audio=open(final_path, 'rb'),
                    title=info.get('title', 'Audio')[:64],
                    performer="YouTube",
                    caption=f"✅ **Download selesai!** - {format_name}\n"
                           f"📊 Ukuran: {file_size_mb}MB"
                )
            else:
                await query.message.reply_video(
                    video=open(final_path, 'rb'),
                    caption=f"✅ **Download selesai!** - {format_name}\n"
                           f"📊 Ukuran: {file_size_mb}MB",
                    supports_streaming=True,
                    width=1920 if quality == '1080' else 1280 if quality == '720' else 640,
                    height=1080 if quality == '1080' else 720 if quality == '720' else 360
                )
            
            await message.edit_text("✅ **Selesai!**")
            
        except Exception as send_error:
            error_msg = str(send_error)
            if "File too large" in error_msg:
                await message.edit_text(
                    f"❌ File terlalu besar ({file_size_mb}MB) untuk dikirim.\n\n"
                    f"💡 Tips:\n"
                    f"• Coba resolusi lebih rendah (720p/360p)\n"
                    f"• Pilih video yang lebih pendek\n"
                    f"• Gunakan format audio saja"
                )
            else:
                await message.edit_text(f"❌ Gagal mengirim file: {error_msg}")
        
        # Cleanup
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
        except Exception as e:
            print(f"Error cleanup: {e}")
            
    except Exception as e:
        error_msg = f"❌ Download error: {str(e)}"
        print(error_msg)
        
        # Error handling yang lebih informatif
        if "requested format is not available" in str(e):
            error_display = (
                "❌ **Resolusi tidak tersedia**\n\n"
                "Video ini tidak tersedia dalam resolusi yang dipilih.\n\n"
                "💡 **Solusi:**\n"
                "• Pilih resolusi lebih rendah (720p/360p)\n"
                "• Coba video lain\n"
                "• Gunakan format audio"
            )
        elif "Private video" in str(e) or "Sign in" in str(e):
            error_display = "❌ Video bersifat privat atau membutuhkan login. Tidak dapat diunduh."
        elif "Video unavailable" in str(e):
            error_display = "❌ Video tidak tersedia atau dihapus."
        else:
            error_display = "❌ Gagal mengunduh. Coba lagi nanti atau gunakan video lain."
        
        try:
            await query.edit_message_text(error_display)
        except:
            await query.message.reply_text(error_display)

def main():
    """Start the bot"""
    print("=" * 50)
    print("🤖 YOUTUBE DOWNLOADER BOT - 1080P SUPPORT")
    print("=" * 50)
    print(f"✅ Bot: {BOT_NAME}")
    print(f"✅ Username: {BOT_USERNAME}")
    print(f"✅ Token: {BOT_TOKEN[:10]}...")
    print("✅ Fitur: Support hingga 1080p Full HD")
    print("✅ Bot berhasil diinisialisasi!")
    print("🚀 Bot sedang berjalan...")
    print("⏹️  Tekan Ctrl+C untuk menghentikan bot")
    print("-" * 50)
    
    try:
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Run bot
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()