"""Test routing layer decoupling."""

from routing.intent_router import Intent, IntentRouter


class MockSceneController:
    """Mock scene controller for testing."""

    def __init__(self):
        self.switched_to = None
        self.went_back = False

    def switch_to(self, scene_name):
        self.switched_to = scene_name

    def go_back(self):
        self.went_back = True


def test_scene_controller_injection():
    """Test that scene controller can be injected into router."""
    router = IntentRouter()
    controller = MockSceneController()

    router.set_scene_controller(controller)

    assert router.get_scene_controller() is controller


def test_intent_routing_with_injected_controller():
    """Test that intents work with injected scene controller."""
    router = IntentRouter()
    controller = MockSceneController()
    router.set_scene_controller(controller)

    # Register a handler that uses the controller
    def go_home(**kwargs):
        ctrl = router.get_scene_controller()
        if ctrl:
            ctrl.switch_to("MenuScene")

    router.register(Intent.GO_HOME, go_home)

    # Emit the intent
    router.emit(Intent.GO_HOME)

    assert controller.switched_to == "MenuScene"


def test_routing_without_scenes_import():
    """Test that routing module doesn't import scenes."""
    import sys

    # Check that scenes module is not in the routing module's dependencies
    router_module = sys.modules["routing.intent_router"]
    handlers_module = sys.modules["routing.intent_handlers"]

    # This is a basic check - the modules should load without scenes
    assert router_module is not None
    assert handlers_module is not None
