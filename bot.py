import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import yt_dlp
import subprocess
import tempfile
import shutil
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
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Create directories if they don't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        
        # Clean up temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text(f'Sorry, an error occurred: {str(e)}')

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
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'Unknown Title')

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
        
        # Clean up temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text(f'Sorry, an error occurred: {str(e)}')

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
