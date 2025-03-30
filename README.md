# docker-ytinstr
YouTube to Instrumental Converter (Telegram Bot)

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
