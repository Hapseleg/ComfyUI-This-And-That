from .py.nodes import *


#  Map all your custom nodes classes with the names that will be displayed in the UI.
NODE_CLASS_MAPPINGS = {
    "Simple Ratio Selector (Hapse)": SimpleRatioSelector,
    "Simple Seed Selector (Hapse)": SimpleSeedSelector,
    "Show Prompt (Hapse)": ShowPrompt,
    # "ttN_textDebug": ttN_textDebug,
}

NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
