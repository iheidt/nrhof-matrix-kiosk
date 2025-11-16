#!/usr/bin/env python3
"""Preload management - background loading of scenes, assets, and caches."""

from nrhof.core.logging_utils import setup_logger
from nrhof.core.thread_pool import create_named_thread, submit_preload_task
from nrhof.scenes.registry import get_preload_list


def start_3d_renderer_preload():
    """Start 3D renderer initialization in background.

    This initializes the Panda3D renderer and loads the D20 model
    early so it's ready when MenuScene is displayed.
    """

    def _init_renderer():
        try:
            import os

            from nrhof.renderers.model_renderer import ModelRenderer

            # Note: Initialization is logged by caller in __main__.py
            renderer = ModelRenderer(width=512, height=512)

            # Load D20 model
            # Go up from nrhof/core/preload_manager.py to project root
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "assets",
                "models",
                "d21.glb",
            )
            if os.path.exists(model_path):
                renderer.load_model(model_path)
                renderer.set_rotation(h=45, p=15, r=0)

                # Store in d20 module's global
                from nrhof.ui.components import d20

                d20._d20_renderer = renderer
                d20._d20_init_attempted = True

                print("[PRELOAD] ✓ 3D renderer preloaded successfully")
            else:
                print(f"[PRELOAD] Warning: D20 model not found at {model_path}")
        except Exception as e:
            print(f"[PRELOAD] Warning: Could not preload 3D renderer: {e}")
            # Mark as attempted so d20 widget doesn't try again
            try:
                from nrhof.ui.components import d20

                d20._d20_init_attempted = True
            except Exception:
                pass

    # Submit to thread pool to cap concurrent preloads
    future = submit_preload_task(_init_renderer, name="3d_renderer_init")
    return future


def start_preload(scene_manager, app_context):
    """Start background scene preloading.

    Args:
        scene_manager: SceneManager instance
        app_context: AppContext instance

    Returns:
        threading.Thread: Waiter thread
    """
    # Initialize preload tracking
    app_context.preload_progress = 0.0
    app_context.preload_done = False

    # Progress callback
    def _progress(done, total):
        app_context.preload_progress = float(done) / float(total)

    # Start preload
    scenes_to_preload = get_preload_list()
    preload_thread = scene_manager.preload_lazy(
        scenes_to_preload,
        progress_cb=_progress,
        sleep_between=0.05,
    )

    # Waiter thread to set preload_done
    def _waiter():
        preload_thread.join()
        app_context.preload_done = True

    waiter_thread = create_named_thread(
        target=_waiter,
        name="preload_waiter",
        daemon=True,
    )
    waiter_thread.start()


def start_webflow_refresh(webflow_cache_manager):
    """Start background Webflow cache refresh.

    Args:
        webflow_cache_manager: WebflowCacheManager instance

    Returns:
        threading.Thread: Refresh thread
    """
    if webflow_cache_manager is None:
        return None

    logger = setup_logger("preload_manager")

    def _refresh():
        logger.info("Starting Webflow cache refresh in background...")
        success = webflow_cache_manager.refresh_all(force=False)
        if success:
            logger.info("Webflow cache refresh complete")
        else:
            logger.warning("Webflow cache refresh failed or skipped")

    refresh_thread = create_named_thread(
        target=_refresh,
        name="webflow_refresh",
        daemon=True,
    )
    refresh_thread.start()
    return refresh_thread
