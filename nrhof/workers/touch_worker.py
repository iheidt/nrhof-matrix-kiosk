#!/usr/bin/env python3
"""Touch input worker - integrates UPDD touch events into the app."""

import asyncio
import time

from nrhof.core.events import EventType

from .base import BaseWorker

try:
    from nrhof.integrations import upddapi

    UPDD_AVAILABLE = True
except ImportError:
    UPDD_AVAILABLE = False


class TouchInputWorker(BaseWorker):
    """Background worker for UPDD touch event integration.

    Registers with UPDD driver to receive touch events and emits them
    on the app event bus for consumption by Pygame scenes.
    """

    def __init__(self, config: dict):
        """Initialize touch worker.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config, logger_name="touch_worker")

        # Check UPDD availability
        if not UPDD_AVAILABLE:
            self.logger.warning("UPDD API not available - touch events disabled")
            self.enabled = False
            return

        # Configuration
        touch_config = config.get("touch", {})
        self.enabled = touch_config.get("enabled", True)
        self.log_events = touch_config.get("log_events", False)

        # Track if running from bundle (for deferred warning if connection fails)
        self._running_from_bundle = False
        if self.enabled and UPDD_AVAILABLE:
            import sys

            self._running_from_bundle = getattr(sys, "frozen", False) or "NRHOF.app" in sys.argv[0]

        self._digitiser_callback = None
        self._event_loop = None
        self._touch_count = 0
        self._last_log_time = 0.0
        self._connected = False
        self._cleaned_up = False  # Guard to prevent double cleanup

        if not self.enabled:
            self.logger.info("Touch worker disabled by config")

    def start(self):
        """Start touch worker."""
        if not self.enabled:
            self.logger.info("Touch worker not started (disabled)")
            return
        super().start()

    def _worker_loop(self):
        """Main worker loop - sets up asyncio event loop and UPDD callbacks."""
        try:
            # Create new event loop for this thread
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            self.logger.info("Initializing UPDD connection...")

            # Register for config events BEFORE opening connection
            self._config_callback = upddapi.create_event_callback_async(
                self._handle_config_event, self._event_loop
            )
            upddapi.TBApiRegisterEvent(0, 0, upddapi._EventConfiguration, self._config_callback)

            # Open connection (will trigger CONFIG_EVENT_CONNECT)
            upddapi.TBApiOpen()

            # Note: BaseWorker.start() already logs 'TouchInputWorker started'
            self.logger.info("Waiting for UPDD driver connection...")
            self._last_log_time = time.time()
            connection_start_time = time.time()

            # Keep event loop alive
            async def keep_alive():
                warned_about_bundle = False
                while self._running:
                    await asyncio.sleep(0.1)

                    # Warn if not connected after 5 seconds and not running from bundle
                    if (
                        not warned_about_bundle
                        and not self._connected
                        and not self._running_from_bundle
                    ):
                        if time.time() - connection_start_time > 5.0:
                            self.logger.warning(
                                "Touch worker enabled but UPDD not connected after 5s. "
                                "Not running from NRHOF.app bundle - UPDD may not send touch events. "
                                "Use 'open /Applications/NRHOF.app' instead of direct execution."
                            )
                            warned_about_bundle = True

                    # Log stats every 30 seconds
                    if self.log_events:
                        current_time = time.time()
                        if current_time - self._last_log_time >= 30.0:
                            elapsed = current_time - self._last_log_time
                            self.logger.info(
                                f"Touch stats: {self._touch_count} events in {elapsed:.1f}s"
                            )
                            self._touch_count = 0
                            self._last_log_time = current_time

            # Run the event loop
            self._event_loop.run_until_complete(keep_alive())

        except Exception as e:
            self.logger.error(f"Touch worker error: {e}", exc_info=True)
        finally:
            self._cleanup()

    async def _handle_config_event(self, event_type, event):
        """Async callback for UPDD configuration events.

        Args:
            event_type: UPDD event type bitmask
            event: _PointerEvent struct with config data
        """
        try:
            config_type = event.pe.config.configEventType

            if config_type == upddapi.CONFIG_EVENT_CONNECT:
                self.logger.info("Connected to UPDD driver")
                self._connected = True

                # Now register for digitiser events
                self.logger.debug("Registering digitiser event callback...")
                self._digitiser_callback = upddapi.create_event_callback_async(
                    self._handle_touch_event, self._event_loop
                )
                result = upddapi.TBApiRegisterEvent(
                    0, 0, upddapi._EventTypeDigitiserEvent, self._digitiser_callback
                )

                if result == 1:
                    self.logger.info("Touch events registered successfully")
                else:
                    self.logger.error(f"Failed to register touch events: {result}")

            elif config_type == upddapi.CONFIG_EVENT_DISCONNECT:
                self.logger.warning("Disconnected from UPDD driver")
                self._connected = False

            elif config_type == upddapi.CONFIG_EVENT_DEVICE:
                self.logger.debug("UPDD device state changed")

        except Exception as e:
            self.logger.error(f"Error handling config event: {e}", exc_info=True)

    async def _handle_touch_event(self, event_type, event):
        """Async callback for UPDD digitiser (touch/pen) events.

        Args:
            event_type: UPDD event type bitmask
            event: _PointerEvent struct with touch data
        """
        try:
            # Access digitiser event data
            de = event.pe.digitiserEvent

            # Determine device type
            is_pen = de.digitizerType == upddapi.DIGITIZER_TYPE_PEN

            # Determine touch action
            touching = de.de.touchEvent.touchingLeft or de.de.touchEvent.touchingRight

            if touching:
                # Track per-stylus state for down vs move
                stylus_key = f"{event.hDevice}_{event.hStylus}"
                if not hasattr(self, "_stylus_states"):
                    self._stylus_states = {}

                if stylus_key in self._stylus_states:
                    action = "move"
                else:
                    action = "down"
                    self._stylus_states[stylus_key] = True
            else:
                action = "up"
                # Clear state on up
                if hasattr(self, "_stylus_states"):
                    stylus_key = f"{event.hDevice}_{event.hStylus}"
                    self._stylus_states.pop(stylus_key, None)

            # Build event data
            touch_data = {
                "action": action,
                "x": de.screenx,
                "y": de.screeny,
                "device": event.hDevice,
                "stylus": event.hStylus,
                "device_type": "pen" if is_pen else "touch",
                "pressure": de.z if de.zSupport else 0,
                "timestamp": event.timestamp,
            }

            # Emit to event bus (thread-safe)
            self.event_bus.emit(EventType.TOUCH_EVENT, touch_data)

            # Stats
            self._touch_count += 1

            # Optional debug logging
            if self.log_events:
                self.logger.debug(
                    f"{touch_data['device_type'].capitalize()} {action}: "
                    f"({de.screenx}, {de.screeny}) "
                    f"device={event.hDevice} stylus={event.hStylus} "
                    f"pressure={touch_data['pressure']}"
                )

        except Exception as e:
            self.logger.error(f"Error handling touch event: {e}", exc_info=True)

    def _cleanup(self):
        """Cleanup UPDD callbacks and event loop."""
        # Guard against double cleanup (called from both stop() and finally block)
        if self._cleaned_up:
            return
        self._cleaned_up = True

        self.logger.info("Touch worker cleanup starting...")

        # Stop event loop first to prevent callbacks during cleanup
        try:
            if self._event_loop and not self._event_loop.is_closed():
                # Stop the loop if it's running
                if self._event_loop.is_running():
                    self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                    # Give it a moment to stop
                    import time

                    time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error stopping event loop: {e}")

        # Unregister callbacks before closing connection
        try:
            if self._digitiser_callback:
                self.logger.debug("Unregistering digitiser callback...")
                upddapi.TBApiUnregisterEvent(self._digitiser_callback)
                self._digitiser_callback = None
        except Exception as e:
            self.logger.error(f"Error unregistering digitiser callback: {e}")

        try:
            if self._config_callback:
                self.logger.debug("Unregistering config callback...")
                upddapi.TBApiUnregisterEvent(self._config_callback)
                self._config_callback = None
        except Exception as e:
            self.logger.error(f"Error unregistering config callback: {e}")

        # NOTE: TBApiClose() has a bug causing segfault on macOS
        # Skip it and let the OS clean up when process exits
        # The callbacks are unregistered which is the important part
        self.logger.debug("Skipping TBApiClose (UPDD bug workaround)")

        # Finally close event loop
        try:
            if self._event_loop and not self._event_loop.is_closed():
                self._event_loop.close()
                self._event_loop = None
                self.logger.debug("Event loop closed")
        except Exception as e:
            self.logger.error(f"Error closing event loop: {e}")

        self.logger.info("Touch worker cleanup complete")
