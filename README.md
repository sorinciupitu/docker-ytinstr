# docker-ytinstr
YouTube to Instrumental Converter (Telegram Bot)

## Fix for YouTube "Sign in to confirm you're not a bot"

YouTube may block automated downloads unless `yt-dlp` receives cookies from a
signed-in browser session. This app now reads a Netscape-format cookies file
from `config/cookies.txt` by default and mounts it into Docker as read-only.
For each request, the bot copies that file into its temporary processing
directory before giving it to `yt-dlp`, because `yt-dlp` may update the cookie
jar while downloading.

1. Keep your Telegram token in a local `.env` file:

   ```bash
   cp .env.example .env
   ```

2. Export YouTube cookies from a browser where you are signed in and save them
   as:

   ```text
   config/cookies.txt
   ```

   The file must be in Netscape cookies format and must not be empty. The
   easiest option is a browser extension such as "Get cookies.txt LOCALLY":
   export cookies for `youtube.com`, then save the downloaded file as
   `config/cookies.txt` in this project folder.

   You can also try exporting with `yt-dlp` from the host machine:

   ```bash
   yt-dlp --cookies-from-browser chrome --cookies config/cookies.txt --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
   ```

3. Rebuild and restart the container so it gets the latest `yt-dlp`:

   ```bash
   docker compose up -d --build
   ```

   If Docker fails during dependency installation with `No space left on
   device`, clear unused Docker build data and retry:

   ```bash
   docker builder prune -af
   docker system prune -af
   docker compose up -d --build
   ```

`config/cookies.txt` and `.env` are ignored by Git because they contain private
credentials.

### Minimum Requirements (for testing/light usage):
- CPU : 4-core modern processor (Intel i5/i7 or AMD Ryzen 5/7)
- RAM : 8GB (16GB recommended)
- Storage : SSD with at least 20GB free space
- GPU : Not required but will significantly speed up processing
### Recommended for Production/Heavy Usage:
- CPU : 8-core processor (Intel i7/i9 or AMD Ryzen 7/9)
- RAM : 16GB+ (32GB ideal for concurrent processing)
- Storage : Fast NVMe SSD with 50GB+ free space
- GPU : NVIDIA GPU with at least 6GB VRAM (RTX 2060 or better) for CUDA acceleration
### Special Notes:
1. GPU Acceleration :
   
   - Demucs performs 4-10x faster with a CUDA-compatible GPU
   - Requires NVIDIA drivers and CUDA toolkit installed
2. Memory Considerations :
   
   - Each concurrent processing job needs ~4GB RAM
   - Audio separation creates temporary files up to 2GB per track
3. Storage :
   
   - Fast storage is crucial as it handles many temporary files
   - Consider RAID 0 or NVMe for better I/O performance
4. Cloud Options :
   
   - AWS: g4dn.xlarge or g5.xlarge instances
   - Google Cloud: n1-standard-8 with T4 GPU
   - Paperspace: P4000 or better instances
