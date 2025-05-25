from .py.nodes import *
from .py.seed import *


NODE_CLASS_MAPPINGS = {
    "Simple Ratio Selector TnT": SimpleRatioSelector,
    "Simple Seed Selector TnT": SimpleSeedSelector,
    "Show Prompt TnT": ShowPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
