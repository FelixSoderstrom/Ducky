"""Voice notification system for code review feedback."""

import logging
import asyncio
import winsound
import io
import wave
from typing import Optional

logger = logging.getLogger("ducky.notifications.voice")


async def generate_speech(text: str, project_id: int) -> None:
    """
    Generate speech from text using ElevenLabs API and play it using winsound.
    
    Args:
        text: The text to convert to speech
        project_id: The project ID to get the API key from
    """
    if not text.strip():
        logger.warning("Empty text provided for speech generation")
        return
        
    logger.info(f"Generating speech for: {text[:50]}...")
    
    try:
        # Import ElevenLabs (only when needed to avoid import errors if not installed)
        from elevenlabs import generate
        
        # Get ElevenLabs API key from database
        api_key = _get_elevenlabs_api_key(project_id)
        if not api_key:
            logger.error("No ElevenLabs API key found - cannot generate speech")
            return
            
        # Generate speech audio using the generate function
        audio_data = await _generate_speech_audio(text, api_key)
        
        if audio_data:
            # Convert to WAV and play with winsound
            await _play_speech_audio(audio_data)
        else:
            logger.error("Failed to generate speech audio")
            
    except ImportError:
        logger.error("ElevenLabs package not installed - cannot generate speech")
    except Exception as e:
        logger.error(f"Failed to generate speech: {str(e)}")


def _get_elevenlabs_api_key(project_id: int) -> Optional[str]:
    """
    Get ElevenLabs API key from database for the given project.
    
    Args:
        project_id: The project ID to look up
        
    Returns:
        API key string or None if not found
    """
    try:
        from ..database.session import get_db
        from ..database.models.projects import Project
        from sqlalchemy import select
        
        with get_db() as session:
            stmt = select(Project.eleven_labs_key).where(Project.id == project_id)
            result = session.execute(stmt)
            api_key = result.scalar_one_or_none()
            
            if api_key:
                return api_key
            else:
                logger.warning(f"No ElevenLabs API key found for project {project_id}")
                return None
                
    except Exception as e:
        logger.error(f"Failed to get ElevenLabs API key from database: {str(e)}")
        return None


async def _generate_speech_audio(text: str, api_key: str) -> Optional[bytes]:
    """
    Generate speech audio using ElevenLabs API.
    
    Args:
        text: Text to convert to speech
        api_key: ElevenLabs API key
        
    Returns:
        Audio data as bytes or None if failed
    """
    try:
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        def generate_audio():
            # Import elevenlabs functions
            from elevenlabs import generate, set_api_key
            
            # Set the API key
            set_api_key(api_key)
            
            # Generate audio using the generate function
            audio_generator = generate(
                text=text,
                voice="JBFqnCBsd6RMkjVDRZzb",  # Default voice ID
                model="eleven_multilingual_v2"
            )
            
            # Collect all chunks from the generator
            audio_chunks = []
            for chunk in audio_generator:
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
            
            # Join all chunks into a single bytes object
            return b''.join(audio_chunks)
        
        audio_data = await loop.run_in_executor(None, generate_audio)
        logger.debug(f"Generated {len(audio_data)} bytes of audio data")
        return audio_data
        
    except Exception as e:
        logger.error(f"Failed to generate speech audio: {str(e)}")
        return None


async def _play_speech_audio(audio_data: bytes) -> None:
    """
    Convert audio data to WAV format and play using winsound.
    
    Args:
        audio_data: Raw audio data from ElevenLabs (usually MP3)
    """
    try:
        # Save to temporary file and play with winsound
        import tempfile
        import os
        
        # First save as MP3, then convert to WAV for winsound
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3_file:
            temp_mp3_file.write(audio_data)
            temp_mp3_path = temp_mp3_file.name
        
        try:
            # Convert MP3 to WAV using pydub (if available) or fallback method
            wav_path = await _convert_mp3_to_wav(temp_mp3_path)
            
            if wav_path:
                # Play the WAV file using winsound
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                )
                logger.debug("Speech playback completed")
                
                # Clean up WAV file
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass
            else:
                logger.error("Failed to convert MP3 to WAV for winsound playback")
                
        finally:
            # Clean up MP3 file
            try:
                os.unlink(temp_mp3_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary audio file: {cleanup_error}")
                
    except Exception as e:
        logger.error(f"Failed to play speech audio: {str(e)}")


async def _convert_mp3_to_wav(mp3_path: str) -> Optional[str]:
    """
    Convert MP3 file to WAV format for winsound compatibility.
    
    Args:
        mp3_path: Path to the MP3 file
        
    Returns:
        Path to the converted WAV file or None if conversion failed
    """
    try:
        import tempfile
        
        # Create temporary WAV file
        temp_wav_fd, temp_wav_path = tempfile.mkstemp(suffix='.wav')
        
        try:
            # Try using pydub for conversion
            from pydub import AudioSegment
            
            # Load MP3 and convert to WAV
            audio = AudioSegment.from_mp3(mp3_path)
            audio.export(temp_wav_path, format="wav")
            
            return temp_wav_path
            
        except ImportError:
            logger.debug("pydub not available, trying ffmpeg directly")
            
            # Try using ffmpeg directly
            import subprocess
            result = subprocess.run([
                'ffmpeg', '-i', mp3_path, '-y', temp_wav_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return temp_wav_path
            else:
                logger.error(f"ffmpeg conversion failed: {result.stderr}")
                return None
                
    except Exception as e:
        logger.error(f"Failed to convert MP3 to WAV: {str(e)}")
        return None 