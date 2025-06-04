"""Voice notification system for code review feedback using Chatterbox TTS."""

import logging
import asyncio
import winsound
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("ducky.notifications.voice")

# Global model instance to avoid repeated loading
_chatterbox_model = None
_model_loading = False


async def generate_speech(text: str, project_id: int) -> None:
    """
    Generate speech from text using Chatterbox TTS and play it using winsound.
    
    Args:
        text: The text to convert to speech
        project_id: The project ID to get voice settings from
    """
    if not text.strip():
        logger.warning("Empty text provided for speech generation")
        return
        
    logger.info(f"Generating speech for: {text[:50]}...")
    
    try:
        # Get voice settings from database
        voice_settings = _get_voice_settings(project_id)
        
        # Initialize Chatterbox model if needed
        model = await _get_chatterbox_model()
        if not model:
            logger.error("Failed to initialize Chatterbox TTS model")
            return
            
        # Generate speech audio using Chatterbox
        audio_data = await _generate_speech_audio(text, model, voice_settings)
        
        if audio_data is not None:
            logger.info("Audio generation successful")
            # Play with winsound
            await _play_speech_audio(audio_data, model.sr)
        else:
            logger.error("Failed to generate speech audio")
            
    except Exception as e:
        logger.error(f"Failed to generate speech: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")


def _get_voice_settings(project_id: int) -> Dict[str, Any]:
    """
    Get voice settings from database for the given project.
    
    Args:
        project_id: The project ID to look up
        
    Returns:
        Dictionary with voice settings including prompt path and parameters
    """
    try:
        from ..database.session import get_db
        from ..database.models.projects import Project
        from sqlalchemy import select
        
        with get_db() as session:
            stmt = select(Project).where(Project.id == project_id)
            result = session.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                logger.warning(f"Project {project_id} not found")
                return _get_default_voice_settings()
            
            # Extract voice settings from project
            # Note: These fields will be added to the Project model
            settings = {
                'voice_prompt_path': getattr(project, 'voice_prompt_path', None),
                'exaggeration': getattr(project, 'voice_exaggeration', 0.5),
                'cfg_weight': getattr(project, 'voice_cfg_weight', 0.5),
            }
            
            return settings
                
    except Exception as e:
        logger.error(f"Failed to get voice settings from database: {str(e)}")
        return _get_default_voice_settings()


def _get_default_voice_settings() -> Dict[str, Any]:
    """Get default voice settings."""
    return {
        'voice_prompt_path': None,
        'exaggeration': 0.5,
        'cfg_weight': 0.5,
    }


async def _get_chatterbox_model():
    """Get or initialize the Chatterbox TTS model with thread safety."""
    global _chatterbox_model, _model_loading
    
    if _chatterbox_model is not None:
        return _chatterbox_model
    
    if _model_loading:
        # Wait for model to finish loading
        while _model_loading:
            await asyncio.sleep(0.1)
        return _chatterbox_model
    
    _model_loading = True
    try:
        logger.info("Initializing Chatterbox TTS model...")
        loop = asyncio.get_event_loop()
        
        def load_model():
            try:
                from chatterbox.tts import ChatterboxTTS
                
                # Initialize with GPU if available, otherwise CPU
                try:
                    model = ChatterboxTTS.from_pretrained(device="cuda")
                    logger.info("Chatterbox TTS model loaded on GPU")
                except Exception:
                    logger.info("GPU not available, loading Chatterbox TTS model on CPU")
                    model = ChatterboxTTS.from_pretrained(device="cpu")
                
                return model
            except ImportError as e:
                logger.error(f"Chatterbox TTS not installed: {e}")
                return None
            except Exception as e:
                logger.error(f"Failed to load Chatterbox TTS model: {e}")
                return None
        
        _chatterbox_model = await loop.run_in_executor(None, load_model)
        
        if _chatterbox_model:
            logger.info("Chatterbox TTS model initialized successfully")
        else:
            logger.error("Failed to initialize Chatterbox TTS model")
        
        return _chatterbox_model
        
    finally:
        _model_loading = False


async def _generate_speech_audio(text: str, model, voice_settings: Dict[str, Any]):
    """
    Generate speech audio using Chatterbox TTS.
    
    Args:
        text: Text to convert to speech
        model: Chatterbox TTS model instance
        voice_settings: Voice configuration settings
        
    Returns:
        Audio tensor or None if failed
    """
    try:
        logger.info(f"Starting Chatterbox audio generation for text: '{text[:50]}...'")
        
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        def generate_audio():
            try:
                # Extract settings
                voice_prompt_path = voice_settings.get('voice_prompt_path')
                exaggeration = voice_settings.get('exaggeration', 0.5)
                cfg_weight = voice_settings.get('cfg_weight', 0.5)
                
                # Generate audio with optional voice cloning
                if voice_prompt_path and os.path.exists(voice_prompt_path):
                    logger.info(f"Using voice prompt from: {voice_prompt_path}")
                    wav = model.generate(
                        text, 
                        audio_prompt_path=voice_prompt_path,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight
                    )
                else:
                    logger.info("Using default voice")
                    wav = model.generate(
                        text,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight
                    )
                
                logger.info("Chatterbox TTS generation completed successfully")
                return wav
                
            except Exception as e:
                logger.error(f"Error in Chatterbox generation: {e}")
                return None
        
        logger.debug("Running Chatterbox audio generation in thread pool...")
        audio_tensor = await loop.run_in_executor(None, generate_audio)
        
        if audio_tensor is not None:
            logger.debug(f"Generated audio tensor with shape: {audio_tensor.shape}")
        
        return audio_tensor
        
    except Exception as e:
        logger.error(f"Failed to generate speech audio with Chatterbox: {str(e)}")
        return None


async def _play_speech_audio(audio_tensor, sample_rate: int) -> None:
    """
    Convert audio tensor to WAV file and play using winsound.
    
    Args:
        audio_tensor: PyTorch audio tensor from Chatterbox
        sample_rate: Sample rate of the audio
    """
    try:
        logger.info(f"Starting audio playback with sample rate: {sample_rate}")
        
        # Save tensor to temporary WAV file
        import tempfile
        import torchaudio
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav_file:
            temp_wav_path = temp_wav_file.name
        
        logger.info(f"Saving audio to temporary file: {temp_wav_path}")
        
        # Save the audio tensor directly to WAV file using torchaudio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: torchaudio.save(temp_wav_path, audio_tensor, sample_rate)
        )
        
        logger.info(f"Audio saved successfully")
        
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


# Utility functions for voice management
async def test_voice_generation(text: str = "Hello, this is a test of the Chatterbox TTS system.") -> bool:
    """
    Test voice generation without requiring a project context.
    
    Args:
        text: Test text to generate
        
    Returns:
        True if test successful, False otherwise
    """
    try:
        logger.info("Testing Chatterbox TTS generation...")
        
        model = await _get_chatterbox_model()
        if not model:
            return False
        
        # Generate test audio
        audio_data = await _generate_speech_audio(text, model, _get_default_voice_settings())
        
        if audio_data is not None:
            await _play_speech_audio(audio_data, model.sr)
            logger.info("✅ Voice generation test successful!")
            return True
        else:
            logger.error("❌ Voice generation test failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Voice generation test failed: {str(e)}")
        return False


def get_model_info() -> Dict[str, Any]:
    """
    Get information about the currently loaded model.
    
    Returns:
        Dictionary with model information
    """
    global _chatterbox_model
    
    if _chatterbox_model is None:
        return {"status": "not_loaded"}
    
    try:
        return {
            "status": "loaded",
            "device": str(_chatterbox_model.device) if hasattr(_chatterbox_model, 'device') else "unknown",
            "sample_rate": getattr(_chatterbox_model, 'sr', 'unknown'),
            "model_type": "Chatterbox TTS"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)} 