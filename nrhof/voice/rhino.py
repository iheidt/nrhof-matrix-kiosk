"""Rhino NLU - Picovoice on-device intent recognition.

Rhino processes complete speech segments and extracts structured intents
without requiring transcription. This is ideal for deterministic commands
like "pause", "next song", "go home", etc.
"""

import os

import numpy as np

from nrhof.core.logging_utils import setup_logger

logger = setup_logger(__name__)

# Debug flag: Set to True to save audio segments for inspection
DEBUG_SAVE_AUDIO = os.environ.get("RHINO_DEBUG_AUDIO", "false").lower() == "true"

# Check if pvrhino is available
try:
    import pvrhino

    HAVE_RHINO = True
except ImportError:
    HAVE_RHINO = False
    logger.warning("pvrhino not available - Rhino NLU will be disabled")


class RhinoNLU:
    """Picovoice Rhino NLU wrapper for intent recognition."""

    def __init__(self, access_key: str | None = None, context_path: str | None = None):
        """Initialize Rhino NLU.

        Args:
            access_key: Picovoice access key (from env if None)
            context_path: Path to .rhn context file

        Raises:
            RuntimeError: If pvrhino not available or initialization fails
        """
        if not HAVE_RHINO:
            raise RuntimeError("pvrhino not available")

        # Get access key from env if not provided
        if access_key is None:
            access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
            if not access_key:
                raise ValueError("PICOVOICE_ACCESS_KEY not set")

        # Validate context path
        if not context_path:
            raise ValueError("context_path required for Rhino")
        if not os.path.exists(context_path):
            raise FileNotFoundError(f"Rhino context file not found: {context_path}")

        self.access_key = access_key
        self.context_path = context_path
        self.rhino = None

        try:
            # Initialize Rhino with context
            self.rhino = pvrhino.create(
                access_key=access_key,
                context_path=context_path,
            )

            logger.info(
                f"Rhino initialized: {self.rhino.sample_rate}Hz, "
                f"frame_length={self.rhino.frame_length} samples, "
                f"context={os.path.basename(context_path)}"
            )
            logger.info(f"Rhino context info: {self.rhino.context_info}")

            # Log available expressions for debugging
            if hasattr(self.rhino, "context_info"):
                import yaml

                try:
                    context_data = yaml.safe_load(self.rhino.context_info)
                    if "context" in context_data and "expressions" in context_data["context"]:
                        intent_names = list(context_data["context"]["expressions"].keys())
                        logger.info(f"Rhino loaded {len(intent_names)} intents: {intent_names}")
                except Exception as e:
                    logger.debug(f"Could not parse context expressions: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize Rhino: {e}")
            raise

    def process_segment(self, pcm: np.ndarray, sample_rate: int) -> tuple[str | None, dict]:
        """Process complete speech segment and extract intent.

        Args:
            pcm: Audio PCM data (int16 numpy array)
            sample_rate: Sample rate (must be 16000Hz for Rhino)

        Returns:
            (intent_name, slots_dict) if understood
            (None, {}) if not understood

        Raises:
            ValueError: If sample rate is not 16000Hz
        """
        if not self.rhino:
            logger.warning("Rhino not initialized")
            return None, {}

        # Validate sample rate
        if sample_rate != self.rhino.sample_rate:
            raise ValueError(f"Rhino requires {self.rhino.sample_rate}Hz, got {sample_rate}Hz")

        # Ensure int16 dtype
        if pcm.dtype != np.int16:
            logger.warning(f"Converting PCM from {pcm.dtype} to int16")
            pcm = pcm.astype(np.int16)

        # Reset Rhino state before processing new segment (critical!)
        try:
            self.rhino.reset()
            logger.info("[Rhino] State reset before processing")
        except Exception as e:
            logger.warning(f"[Rhino] Failed to reset: {e}")

        # Add minimal silence padding to ensure frame alignment
        # CRITICAL: Total length must be a multiple of frame_length (512)
        # Worker already adds 800ms post-speech silence, so we just need alignment padding
        remainder = len(pcm) % self.rhino.frame_length
        if remainder != 0:
            # Add padding to reach next multiple of 512
            padding_samples = self.rhino.frame_length - remainder
            silence_padding = np.zeros(padding_samples, dtype=np.int16)
            pcm_with_padding = np.concatenate([pcm, silence_padding])
        else:
            pcm_with_padding = pcm
            padding_samples = 0

        # Verify total is perfect multiple
        assert (
            len(pcm_with_padding) % self.rhino.frame_length == 0
        ), f"Total samples {len(pcm_with_padding)} not divisible by {self.rhino.frame_length}"

        total_frames = len(pcm_with_padding) // self.rhino.frame_length
        logger.info(
            f"[Rhino] Processing segment: {len(pcm)} samples ({len(pcm)/16000:.2f}s) "
            f"+ {padding_samples} alignment padding = {len(pcm_with_padding)} total "
            f"({total_frames} frames @ {self.rhino.frame_length} samples/frame)"
        )

        # Debug: Save audio to file for inspection
        if DEBUG_SAVE_AUDIO:
            try:
                import time
                import wave

                debug_file = f"/tmp/rhino_debug_{int(time.time())}.wav"
                with wave.open(debug_file, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(16000)
                    wf.writeframes(pcm_with_padding.tobytes())
                logger.info(f"[Rhino DEBUG] Saved audio to {debug_file}")
            except Exception as e:
                logger.warning(f"[Rhino DEBUG] Could not save audio: {e}")

        # Process audio frame by frame
        frame_length = self.rhino.frame_length
        is_finalized = False

        try:
            # Feed frames to Rhino until finalized
            # CRITICAL: Rhino requires EXACT 512-sample frames
            # We must discard incomplete frames, NOT pad them
            frames_processed = 0
            for i in range(0, len(pcm_with_padding), frame_length):
                frame = pcm_with_padding[i : i + frame_length]

                # Discard incomplete frames - Rhino cannot process them
                if len(frame) != frame_length:
                    logger.debug(
                        f"[Rhino] Discarding incomplete frame: {len(frame)} samples "
                        f"(expected {frame_length})"
                    )
                    break

                # Convert to list for Rhino API (must be exact frame_length)
                frame_list = frame.tolist()
                is_finalized = self.rhino.process(frame_list)
                frames_processed += 1

                # Log progress every 30 frames (~1 second)
                if frames_processed % 30 == 0:
                    logger.debug(
                        f"[Rhino] Processed {frames_processed} frames ({frames_processed*512/16000:.2f}s)..."
                    )

                if is_finalized:
                    processing_time_s = frames_processed * 512 / 16000
                    logger.info(
                        f"[Rhino] ✓ Finalized after {frames_processed} frames "
                        f"({processing_time_s:.2f}s, {(processing_time_s/len(pcm)*16000)*100:.1f}% of audio duration)"
                    )
                    break

            # Get inference if finalized
            if is_finalized:
                inference = self.rhino.get_inference()

                if inference.is_understood:
                    intent = inference.intent
                    slots = inference.slots if inference.slots else {}

                    logger.info(f"[Rhino] Recognized intent='{intent}' slots={slots}")
                    return intent, slots
                else:
                    logger.debug("[Rhino] Speech not understood")
                    return None, {}
            else:
                logger.warning(
                    f"[Rhino] Inference not finalized after {frames_processed} frames "
                    f"({len(pcm_with_padding)} samples, {len(pcm_with_padding)/16000:.2f}s)"
                )
                # Try to get inference anyway to see what Rhino has
                try:
                    inference = self.rhino.get_inference()
                    logger.debug(
                        f"[Rhino] Partial inference: is_understood={inference.is_understood}, "
                        f"intent={inference.intent if hasattr(inference, 'intent') else 'N/A'}"
                    )
                except Exception as e:
                    logger.debug(f"[Rhino] Could not get partial inference: {e}")
                return None, {}

        except Exception as e:
            logger.error(f"Rhino processing failed: {e}")
            return None, {}

    def reset(self):
        """Reset Rhino state for next utterance."""
        if self.rhino:
            try:
                self.rhino.reset()
                logger.debug("Rhino state reset")
            except Exception as e:
                logger.warning(f"Error resetting Rhino: {e}")

    def cleanup(self):
        """Cleanup Rhino resources."""
        if self.rhino:
            try:
                self.rhino.delete()
                logger.debug("Rhino cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up Rhino: {e}")
            finally:
                self.rhino = None


def create_rhino(access_key: str | None = None, context_path: str | None = None) -> RhinoNLU | None:
    """Create Rhino NLU instance.

    Args:
        access_key: Optional Picovoice access key
        context_path: Path to .rhn context file

    Returns:
        RhinoNLU instance or None if pvrhino not available
    """
    if not HAVE_RHINO:
        logger.warning("pvrhino not available, Rhino disabled")
        return None

    try:
        return RhinoNLU(access_key=access_key, context_path=context_path)
    except Exception as e:
        logger.error(f"Failed to create Rhino: {e}")
        return None
