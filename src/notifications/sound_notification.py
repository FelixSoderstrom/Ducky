"""Sound notification system for code review feedback."""

import logging
import asyncio
import winsound
from pathlib import Path

logger = logging.getLogger("ducky.notifications.sound")


async def play_notification_sound() -> None:
    """
    Play the notification sound file using Windows winsound.
    
    Uses winsound.PlaySound() to play the pluck.wav file.
    """
    try:
        # Get the path to the audio file
        current_dir = Path(__file__).parent.parent
        audio_path = current_dir / "ui" / "assets" / "audio" / "pluck.wav"
        
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return
        
        logger.info(f"Playing notification sound: {audio_path}")
        
        # Play the WAV file using winsound
        await _play_wav_file(str(audio_path))
        
    except Exception as e:
        logger.error(f"Failed to play notification sound: {str(e)}")


async def _play_wav_file(audio_path: str) -> None:
    """
    Play WAV file using winsound in a thread to avoid blocking the event loop.
    
    Args:
        audio_path: Path to the WAV file to play
    """
    try:
        # Run winsound.PlaySound in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: winsound.PlaySound(audio_path, winsound.SND_FILENAME)
        )
        logger.debug("Sound playback completed")
        
    except Exception as e:
        logger.error(f"Failed to play WAV file with winsound: {str(e)}") 