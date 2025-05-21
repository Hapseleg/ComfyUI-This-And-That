#  Package Modules
import json
import os
import csv
import random


MAX_SEED_NUM = 18446744073709552000


# SimpleRatioSelector
def read_ratio_presets():
    p = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(p, "../preset_ratios.csv")
    preset_ratios_dict = {}
    labels = []
    with open(file_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter="|", quotechar='"')
        for row in reader:
            preset_ratios_dict[row[0]] = [row[1],row[2]]
            labels.append(row[0])
    return preset_ratios_dict, labels

class SimpleRatioSelector:
    @classmethod
    def INPUT_TYPES(s):
        s.ratio_presets = read_ratio_presets()[1]
        s.preset_ratios_dict = read_ratio_presets()[0]
        return {"required": { "select_preset": (s.ratio_presets, {"default": s.ratio_presets[0]}),
                              "orientation": (["Portrait","Landscape"], {"default": "Portrait"})
                            },
                "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO", "prompt": "PROMPT"}
                }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    CATEGORY = "utils/this_and_that"
    FUNCTION = "run"

    def run(self, select_preset, orientation):
        dimensions = self.preset_ratios_dict[select_preset]

        height = dimensions[0]
        width = dimensions[1]

        if orientation == "Landscape":
            height = dimensions[1]
            width = dimensions[0]

        return (int(width), int(height))

# SimpleSeedSelector

# TODO:
#find ud af om man kan hide control before generate
#sæt den til altid randomize
#ændre værdien på seed tilbage til det før hvis mode er på fixed
class SimpleSeedSelector:
    def __init__(self):
        self.num = 0
    
    @classmethod
    def INPUT_TYPES(s):
        # s.random_number = random.randint(1, MAX_SEED_NUM)
        return {
            "required": {
                "seed": ("INT", {"default": 1, "min": 1, "max": MAX_SEED_NUM}),
                "mode": ("BOOLEAN", {"default": True, "label_on": "fixed_seed", "label_off": "randomize_seed"}),
                "global_seed": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
            "unique_id": "UNIQUE_ID",
            "prompt": "PROMPT", 
            "extra_pnginfo": "EXTRA_PNGINFO",
        }
        }

    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("seed_int", "seed_float")
    FUNCTION = "run"

    CATEGORY = "utils/this_and_that"

    OUTPUT_NODE = True

    def run(self, seed, mode, global_seed, **kwargs):
        
        # Force update
        def IS_CHANGED(self):
                self.num += 1 if self.num == 0 else -1
                return self.num
        setattr(self.__class__, 'IS_CHANGED', IS_CHANGED)

        return (int(seed), float(seed))
    
    
# class SimpleSeedSelector:
#     @classmethod
#     def INPUT_TYPES(s):
#         return {
#             "required": {
#                 "value": ("INT", {"default": 1, "min": 1, "max": MAX_SEED_NUM}),
#                 "mode": ("BOOLEAN", {"default": True, "label_on": "fixed_seed", "label_off": "randomize_seed"}),
#                 "global_seed": ("BOOLEAN", {"default": True}),
#             },
#             # "hidden": {
#             #     "unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO", "prompt": "PROMPT"
#             #     }
#         }

#     RETURN_TYPES = ("INT")
#     RETURN_NAMES = ("seed_int")
#     FUNCTION = "run"
#     CATEGORY = "utils/this_and_that"
#     OUTPUT_NODE = True

#     def run(self, value, mode, global_seed):
#         print(value)
#         value = 2
#         return (1)


# https://github.com/comfyanonymous/ComfyUI/issues/1475
class ShowPrompt:
    def __init__(self):
        self.num = 0
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO", "unique_id": "UNIQUE_ID",}
        }

    CATEGORY = "utils/this_and_that"
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "run"
    OUTPUT_NODE = True

    def run(self, unique_id, text="", prompt=None, **kwargs):
        # Force update
        def IS_CHANGED(self):
                self.num += 1 if self.num == 0 else -1
                return self.num
        setattr(self.__class__, 'IS_CHANGED', IS_CHANGED)
        
        
        clean_prompt = prompt
        for n in clean_prompt:
            if n == unique_id:
                clean_prompt[n]["inputs"]["display"] = ""
                continue
        text = json.dumps(clean_prompt)
        return {"ui": {"text": text}}

NODE_CLASS_MAPPINGS = {
    "Simple Ratio Selector (Hapse)": SimpleRatioSelector,
    "Simple Seed Selector (Hapse)": SimpleSeedSelector,
    "Show Prompt (Hapse)": ShowPrompt,
    # "ttN_textDebug": ttN_textDebug,
}