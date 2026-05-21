import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import yt_dlp
import subprocess
import tempfile
import shutil
import imageio_ffmpeg
from dotenv import load_dotenv  # Add this import
from demucs_separator import DemucsVocalSeparator  # Import the Demucs separator

# Load environment variables from .env file
load_dotenv()  # Add this line

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DEFAULT_COOKIES_FILE = os.path.join(BASE_DIR, "config", "cookies.txt")
YTDLP_COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE", DEFAULT_COOKIES_FILE)
YTDLP_COOKIES_FROM_BROWSER = os.environ.get("YTDLP_COOKIES_FROM_BROWSER")
FFMPEG_LOCATION = os.environ.get("FFMPEG_LOCATION")
YTDLP_REQUIRE_COOKIES = os.environ.get("YTDLP_REQUIRE_COOKIES", "1").lower() not in (
    "0",
    "false",
    "no",
)

# Create directories if they don't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_ffmpeg_location():
    """Return a usable ffmpeg binary path for yt-dlp."""
    if FFMPEG_LOCATION:
        return FFMPEG_LOCATION

    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.warning("Could not locate bundled ffmpeg: %s", e)
        return None

def configure_ytdlp_auth(ydl_opts, writable_dir):
    """Attach YouTube cookies to yt-dlp or fail with an actionable message."""
    if YTDLP_COOKIES_FILE and os.path.exists(YTDLP_COOKIES_FILE) and os.path.getsize(YTDLP_COOKIES_FILE) > 0:
        cookie_copy = os.path.join(writable_dir, 'cookies.txt')
        shutil.copy2(YTDLP_COOKIES_FILE, cookie_copy)
        ydl_opts['cookiefile'] = cookie_copy
        logger.info("Using yt-dlp cookies file copy: %s", cookie_copy)
        return

    if YTDLP_COOKIES_FROM_BROWSER:
        ydl_opts['cookiesfrombrowser'] = tuple(
            item.strip() for item in YTDLP_COOKIES_FROM_BROWSER.split(':') if item.strip()
        )
        logger.info("Using yt-dlp cookies from browser: %s", YTDLP_COOKIES_FROM_BROWSER)
        return

    message = (
        "YouTube cookies are missing. Export cookies from a signed-in browser "
        f"and save them on this machine as config/cookies.txt. Inside Docker "
        f"the bot expects the file at {YTDLP_COOKIES_FILE}."
    )

    if YTDLP_REQUIRE_COOKIES:
        raise RuntimeError(message)

    logger.warning(message)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        'Hi! I can convert YouTube songs to instrumental versions.\n'
        'Just send me a YouTube URL, and I\'ll do the rest!\n\n'
        'You can also specify a vocal removal method by using one of these commands:\n'
        '/standard [URL] - Balanced vocal removal (default)\n'
        '/aggressive [URL] - Stronger vocal removal (may affect quality)\n'
        '/gentle [URL] - Gentle vocal removal (preserves more original sound)\n'
        '/karaoke [URL] - Karaoke-style vocal removal'
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text(
        'Send me a YouTube URL, and I\'ll convert it to an instrumental version by removing vocals.\n\n'
        'Available commands:\n'
        '/standard [URL] - Balanced vocal removal (default)\n'
        '/aggressive [URL] - Stronger vocal removal (may affect quality)\n'
        '/gentle [URL] - Gentle vocal removal (preserves more original sound)\n'
        '/karaoke [URL] - Karaoke-style vocal removal'
    )

def process_with_method(update: Update, context: CallbackContext, method='standard') -> None:
    """Process YouTube URL with specified vocal removal method."""
    if not context.args:
        update.message.reply_text(f'Please provide a YouTube URL after the /{method} command.')
        return
    
    url = context.args[0]
    if not url.startswith(('http://', 'https://')):
        update.message.reply_text('Please send a valid YouTube URL.')
        return
    
    update.message.reply_text(f'Processing your request using {method} vocal removal. This may take a few minutes...')
    
    temp_dir = None
    try:
        # Create temporary directories for processing
        temp_dir = tempfile.mkdtemp()
        download_path = os.path.join(temp_dir, 'audio.%(ext)s')
        
        # Download the audio
        title = download_youtube_audio(url, download_path)
        update.message.reply_text(f'Downloaded: {title}')
        
        # Find the downloaded file (it will have .mp3 extension)
        downloaded_file = os.path.join(temp_dir, 'audio.mp3')
        
        # Process the audio to remove vocals
        update.message.reply_text('Removing vocals...')
        
        # Create a progress callback function to update the user
        progress_message = update.message.reply_text('Progress: 0%')
        
        def progress_callback(percent):
            progress_message.edit_text(f'Progress: {percent}%')
        
        instrumental_file = process_audio(downloaded_file, temp_dir, method, progress_callback, title)
        
        if instrumental_file and os.path.exists(instrumental_file):
            # Send the instrumental file back to the user
            update.message.reply_text('Here is your instrumental version:')
            with open(instrumental_file, 'rb') as audio:
                update.message.reply_audio(audio, title=f"{title} (Instrumental - {method})")
        else:
            update.message.reply_text('Sorry, there was an error processing the audio.')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text(f'Sorry, an error occurred: {str(e)}')
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

def standard_command(update: Update, context: CallbackContext) -> None:
    """Process with standard vocal removal."""
    process_with_method(update, context, 'standard')

def aggressive_command(update: Update, context: CallbackContext) -> None:
    """Process with aggressive vocal removal."""
    process_with_method(update, context, 'aggressive')

def gentle_command(update: Update, context: CallbackContext) -> None:
    """Process with gentle vocal removal."""
    process_with_method(update, context, 'gentle')

def karaoke_command(update: Update, context: CallbackContext) -> None:
    """Process with karaoke-style vocal removal."""
    process_with_method(update, context, 'karaoke')

def download_youtube_audio(url, output_path):
    """Download audio from YouTube URL."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',  # Highest MP3 quality
        }],
        'outtmpl': output_path,
        'noplaylist': True,  # Add this to prevent playlist downloads
    }

    ffmpeg_location = get_ffmpeg_location()
    if ffmpeg_location:
        ydl_opts['ffmpeg_location'] = ffmpeg_location
        logger.info("Using ffmpeg binary: %s", ffmpeg_location)

    configure_ytdlp_auth(ydl_opts, os.path.dirname(output_path))
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get('title', 'Unknown Title')
    except yt_dlp.utils.DownloadError as exc:
        error_text = str(exc)
        if (
            "Sign in to confirm" in error_text
            or "HTTP Error 403" in error_text
            or "Forbidden" in error_text
        ):
            raise RuntimeError(
                "YouTube blocked the download. Export fresh cookies from a signed-in "
                "browser and save them as config/cookies.txt, then restart the bot."
            ) from exc
        raise

def process_audio(input_file, output_dir, method='standard', progress_callback=None, original_title=None):
    """Remove vocals using Demucs for high-quality source separation."""
    try:
        # Initialize the Demucs separator
        separator = DemucsVocalSeparator()
        
        # Use Demucs to separate vocals from the music
        instrumental_file = separator.separate(input_file, output_dir, method, progress_callback, original_title)
        
        return instrumental_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing audio: {e}")
        return None

def process_youtube_url(update: Update, context: CallbackContext) -> None:
    """Process YouTube URL and send back instrumental version using standard method."""
    url = update.message.text
    
    if not url.startswith(('http://', 'https://')):
        update.message.reply_text('Please send a valid YouTube URL.')
        return
    
    update.message.reply_text('Processing your request using standard vocal removal. This may take a few minutes...')
    
    temp_dir = None
    try:
        # Create temporary directories for processing
        temp_dir = tempfile.mkdtemp()
        download_path = os.path.join(temp_dir, 'audio.%(ext)s')
        
        # Download the audio
        title = download_youtube_audio(url, download_path)
        update.message.reply_text(f'Downloaded: {title}')
        
        # Find the downloaded file (it will have .mp3 extension)
        downloaded_file = os.path.join(temp_dir, 'audio.mp3')
        
        # Process the audio to remove vocals
        update.message.reply_text('Removing vocals...')
        
        # Create a progress callback function to update the user
        progress_message = update.message.reply_text('Progress: 0%')
        
        def progress_callback(percent):
            progress_message.edit_text(f'Progress: {percent}%')
        
        instrumental_file = process_audio(downloaded_file, temp_dir, 'standard', progress_callback, title)
        
        if instrumental_file and os.path.exists(instrumental_file):
            # Send the instrumental file back to the user
            update.message.reply_text('Here is your instrumental version:')
            with open(instrumental_file, 'rb') as audio:
                update.message.reply_audio(audio, title=f"{title} (Instrumental)")
        else:
            update.message.reply_text('Sorry, there was an error processing the audio.')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text(f'Sorry, an error occurred: {str(e)}')
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("standard", standard_command))
    dispatcher.add_handler(CommandHandler("aggressive", aggressive_command))
    dispatcher.add_handler(CommandHandler("gentle", gentle_command))
    dispatcher.add_handler(CommandHandler("karaoke", karaoke_command))

    # on non command i.e message - process YouTube URL with standard method
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_youtube_url))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
