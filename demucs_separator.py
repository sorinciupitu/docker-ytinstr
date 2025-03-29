import os
import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)

class DemucsVocalSeparator:
    """Class for separating vocals from music using Demucs."""
    
    def __init__(self, model_name="htdemucs"):
        """Initialize the Demucs separator with the specified model.
        
        Args:
            model_name (str): The name of the Demucs model to use.
                Options include: 'htdemucs' (default), 'htdemucs_ft', 'mdx_extra', etc.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Load the model
        try:
            self.model = get_model(model_name)
            self.model.to(self.device)
            logger.info(f"Loaded Demucs model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load Demucs model: {e}")
            raise
    
    def separate(self, input_file, output_dir, method='standard', progress_callback=None, original_title=None):
        """Separate vocals from the music file.
        
        Args:
            input_file (str): Path to the input audio file.
            output_dir (str): Directory to save the separated audio.
            method (str): Separation method ('standard', 'aggressive', 'gentle', 'karaoke').
                This affects how the separation is performed.
            progress_callback (callable, optional): Function to call with progress updates (0-100).
                Used for Telegram progress reporting.
            original_title (str, optional): Original title of the YouTube video.
                Used to preserve the original title in the output filename.
                
        Returns:
            str: Path to the instrumental file.
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Load audio
            logger.info(f"Loading audio file: {input_file}")
            waveform, sample_rate = torchaudio.load(input_file)
            
            # Convert to expected format (batch, channels, time)
            if waveform.dim() == 2:
                waveform = waveform.unsqueeze(0)
            
            # Move to device
            waveform = waveform.to(self.device)
            
            # Apply model with progress reporting
            logger.info("Applying Demucs model for source separation")
            
            # Report initial progress
            if progress_callback:
                progress_callback(10)
            
            # Apply the model
            sources = apply_model(self.model, waveform, device=self.device)
            
            # Report progress after model application
            if progress_callback:
                progress_callback(80)
            
            # Move to CPU
            sources = sources.cpu()
            
            # Report completion
            if progress_callback:
                progress_callback(100)
            else:
                # Use tqdm for local progress display if no callback provided
                with tqdm(total=100, desc="Processing audio", ncols=100, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
                    pbar.update(100)
            
            # Get the instrumental track (no vocals)
            # Demucs typically outputs sources in this order: [drums, bass, other, vocals]
            # We want everything except vocals for the instrumental
            
            # Adjust the mix based on the method
            if method == 'aggressive':
                # Completely remove vocals
                instrumental = sources[:, :3].sum(dim=1)  # Sum all except vocals
            elif method == 'gentle':
                # Keep a small amount of vocals
                instrumental = sources[:, :3].sum(dim=1) + 0.1 * sources[:, 3]  # Add a bit of vocals back
            elif method == 'karaoke':
                # Focus on drums and bass, reduce other elements
                instrumental = 1.2 * sources[:, 0] + 1.2 * sources[:, 1] + 0.8 * sources[:, 2]  # Emphasize rhythm
            else:  # standard
                # Balanced instrumental
                instrumental = sources[:, :3].sum(dim=1)  # Sum all except vocals
            
            # Generate output file path with INSTRUMENTAL suffix
            if original_title:
                # Use the original YouTube video title if provided
                # Preserve the exact YouTube title and add INSTRUMENTAL suffix
                base_name = original_title
            else:
                # Fallback to the input filename if no original title is provided
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                
            # Ensure we use the exact YouTube title with INSTRUMENTAL suffix
            # The filename should be exactly the same as the YouTube title with INSTRUMENTAL suffix
            # No sanitization or modification of the original title
            # Use the raw YouTube title and just append INSTRUMENTAL suffix
            instrumental_file = os.path.join(output_dir, f"{base_name} INSTRUMENTAL.mp3")
            logger.info(f"Output filename: {instrumental_file}")
            logger.info(f"Using title for output: {base_name}")
            
            # Save the instrumental track
            logger.info(f"Saving instrumental to: {instrumental_file}")
            torchaudio.save(
                instrumental_file,
                instrumental.squeeze(0),  # Remove batch dimension
                sample_rate,
                format="mp3"  # MP3 format without compression parameter
            )
            
            return instrumental_file
            
        except Exception as e:
            logger.error(f"Error in Demucs separation: {e}")
            return None
