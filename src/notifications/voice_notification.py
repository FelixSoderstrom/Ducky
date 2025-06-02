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
        # Import ElevenLabs client (only when needed to avoid import errors if not installed)
        from elevenlabs.client import ElevenLabs
        
        # Get ElevenLabs API key from database
        api_key = _get_elevenlabs_api_key(project_id)
        if not api_key:
            logger.error("No ElevenLabs API key found - cannot generate speech")
            return
            
        # Generate speech audio using the official API pattern
        audio_data = await _generate_speech_audio(text, api_key)
        
        if audio_data:
            logger.info(f"Audio generation successful - {len(audio_data)} bytes received")
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
    Generate speech audio using ElevenLabs API following official documentation.
    
    Args:
        text: Text to convert to speech
        api_key: ElevenLabs API key
        
    Returns:
        Audio data as bytes or None if failed
    """
    try:
        logger.info(f"Starting audio generation for text: '{text[:50]}...'")
        
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        def generate_audio():
            logger.debug("Importing ElevenLabs client...")
            # Import and use the official API pattern from documentation
            from elevenlabs.client import ElevenLabs
            
            logger.debug("Creating ElevenLabs client...")
            # Create client instance with API key
            client = ElevenLabs(api_key=api_key)
            
            logger.info("Making API call to ElevenLabs...")
            # Use PCM format to avoid conversion issues - supported in version 2.1.0
            audio = client.text_to_speech.convert(
                text=text,
                voice_id="JBFqnCBsd6RMkjVDRZzb",  # Default voice ID
                model_id="eleven_multilingual_v2",
                output_format="pcm_16000"  # 16kHz PCM format for free tier compatibility
            )
            
            logger.info("ElevenLabs API call completed, processing response...")
            
            # Audio is returned as bytes or generator, handle both cases
            if hasattr(audio, '__iter__') and not isinstance(audio, (str, bytes)):
                logger.debug("Audio response is a generator, collecting chunks...")
                # It's a generator, collect all chunks
                audio_chunks = []
                chunk_count = 0
                for chunk in audio:
                    if isinstance(chunk, bytes):
                        audio_chunks.append(chunk)
                        chunk_count += 1
                        if chunk_count % 10 == 0:  # Log every 10 chunks
                            logger.debug(f"Collected {chunk_count} audio chunks...")
                
                logger.info(f"Collected {chunk_count} audio chunks, joining...")
                result = b''.join(audio_chunks)
                logger.info(f"Joined audio chunks into {len(result)} bytes")
                return result
            else:
                logger.debug("Audio response is already bytes")
                # It's already bytes
                return audio
        
        logger.debug("Running audio generation in thread pool...")
        audio_data = await loop.run_in_executor(None, generate_audio)
        logger.debug(f"Generated {len(audio_data)} bytes of PCM audio data")
        return audio_data
        
    except Exception as e:
        logger.error(f"Failed to generate speech audio: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


async def _play_speech_audio(audio_data: bytes) -> None:
    """
    Convert PCM audio data to WAV format and play using winsound.
    
    Args:
        audio_data: Raw PCM audio data from ElevenLabs
    """
    try:
        logger.info(f"Starting audio playback with {len(audio_data)} bytes of PCM data")
        
        # Convert PCM to WAV format directly (no need for MP3 conversion)
        logger.debug("Converting PCM to WAV format...")
        wav_data = _pcm_to_wav(audio_data)
        logger.info(f"PCM to WAV conversion successful - {len(wav_data)} bytes of WAV data")
        
        # Save to temporary file and play with winsound
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav_file:
            temp_wav_file.write(wav_data)
            temp_wav_path = temp_wav_file.name
        
        logger.info(f"WAV file saved to: {temp_wav_path}")
        
        try:
            # Verify the file exists and has content
            if os.path.exists(temp_wav_path):
                file_size = os.path.getsize(temp_wav_path)
                logger.info(f"WAV file verified - size: {file_size} bytes")
            else:
                logger.error("WAV file was not created!")
                return
            
            # Play the WAV file using winsound
            logger.info("Starting winsound playback...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: winsound.PlaySound(temp_wav_path, winsound.SND_FILENAME)
            )
            logger.info("winsound.PlaySound() completed successfully!")
            
        finally:
            # Clean up WAV file
            try:
                os.unlink(temp_wav_path)
                logger.debug("Temporary WAV file cleaned up")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary audio file: {cleanup_error}")
                
    except Exception as e:
        logger.error(f"Failed to play speech audio: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    Convert raw PCM data to WAV format for winsound compatibility.
    
    Args:
        pcm_data: Raw PCM audio data from ElevenLabs
        sample_rate: Sample rate in Hz (default: 16000 for pcm_16000 format - free tier compatible)
        channels: Number of audio channels (default: 1 for mono)
        sample_width: Sample width in bytes (default: 2 for 16-bit PCM)
        
    Returns:
        WAV-formatted audio data as bytes
    """
    try:
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        
        wav_buffer.seek(0)
        return wav_buffer.read()
        
    except Exception as e:
        logger.error(f"Failed to convert PCM to WAV: {str(e)}")
        raise 