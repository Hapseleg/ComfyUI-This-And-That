import random
import server
from enum import Enum

MAX_SEED_NUM = 18446744073709552000
GLOBAL_SEED_NODE = ""

class SGmode(Enum):
    FIX = 1
    INCR = 2
    DECR = 3
    RAND = 4


class SeedGenerator:
    def __init__(self, base_value, action):
        print("SeedGenerator")
        self.base_value = base_value

        match action:
            case "fixed":
                self.action = SGmode.FIX
            case "randomize":
                self.action = SGmode.RAND
            case _:
                return ""

    def next(self):
        print("next")
        seed = self.base_value
        self.base_value = random.randint(0, MAX_SEED_NUM)

        return seed


def control_seed(v, action, seed_is_global):
    print("control_seed")
    action = v['inputs']['action'] if seed_is_global else action
    value = v['inputs']['value'] if seed_is_global else v['inputs']['seed_num']

    value = random.randint(0, MAX_SEED_NUM)
    if seed_is_global:
        v['inputs']['value'] = value

    return value

# seed_widgets contains all the node id that has a seed input and the "position" in that node
# so for example "KSampler (Advanced) with the node id 10 would be 10:1 because its noise_seed input is the 2nd input from the top (so thats index 1)"
def has_global_seed_node(json_data):
    try: 
        wf = json_data['extra_data']['extra_pnginfo']['workflow']
        global_seed_widget_id = wf['global_seed_widget_id']
        global_seed_widget_fixed_enabled = wf['global_seed_widget_fixed_enabled']
        global_seed_widget_global_enabled = wf['global_seed_widget_global_enabled']
        # seedNodeId, seedNodeRandomizeEnabled, seedNodeGlobalEnabled
        # seed_node_id = next(iter(global_seed_widget_id))
        # global_activated = global_seed_widget_id[seed_node_id]
        # return seed_node_id, randomize_enabled, global_activated
        #seedNodeRandomizeEnabled seedNodeGlobalEnabled
        return global_seed_widget_id, global_seed_widget_fixed_enabled, global_seed_widget_global_enabled
        # seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    except:
        return -1, False, False
    
    
    # seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    # has_node = False
    # global_active = False
    # # check if theres any nodes that has "seed" input/output/etc in it (they are added in the widgets.js)
    # if len(seed_widget_map) > 0:
    #     #Simple Seed Selector TnT
    #     #{'3': 0, '10': 0}
    #     # {'id': 11, 'type': 'KSamplerAdvanced', 'pos': [918.8762817382812, 80.12080383300781], 'size': [244.748046875, 334], 'flags': {}, 'order': 5, 'mode': 0, 'inputs': [{...}, {...}, {...}, {...}], 'outputs': [{...}], 'properties': {'Node name for S&R': 'KSamplerAdvanced'}, 'widgets_values': ['enable', 771159135202153, 'randomize', 1, 1, 'euler', 'normal', 0, 10000, 'disable']}
    #     nodes = json_data['extra_data']['extra_pnginfo']['workflow']['nodes']
        
    #     for node in nodes:
    #         node_id_str = str(node['id'])
    #         if node_id_str in seed_widget_map:
    #             # check if "Simple Seed Selector TnT" is anywhere to be found in the workflow
    #             if node['type'] == node_name:
    #                 has_node = True
                    # check if "global_seed is turned on in the node"

        
    # return has_node, global_active


def prompt_seed_update(json_data):
    seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    
    # check if theres any nodes that has "seed" input/output/etc in it (they are added in the widgets.js)
    if len(seed_widget_map) == 0:
        return False
    
    # check if "Simple Seed Selector TnT" is anywhere to be found in the workflow
    #Simple Seed Selector TnT
    #{'3': 0, '10': 0}

    workflow = json_data['extra_data']['extra_pnginfo']['workflow']
    # seed_widget_map = workflow['seed_widgets']
    value = None
    mode = None
    node = None
    action = None
    seed_is_global = False

    for k, v in json_data['prompt'].items():
        if 'class_type' not in v:
            continue

        cls = v['class_type']

        if cls == 'Show Prompt (Hapse)':
            mode = v['inputs']['mode']
            action = v['inputs']['action']
            value = v['inputs']['value']
            node = k, v
            seed_is_global = True

    # control before generated
    if mode is not None and mode and seed_is_global:
        value = control_seed(node[1], action, seed_is_global)

    if seed_is_global:
        if value is not None:
            seed_generator = SeedGenerator(value, action)

            for k, v in json_data['prompt'].items():
                for k2, v2 in v['inputs'].items():
                    if isinstance(v2, str) and '$GlobalSeed.value$' in v2:
                        v['inputs'][k2] = v2.replace('$GlobalSeed.value$', str(value))

                if k not in seed_widget_map:
                    continue

                if 'seed_num' in v['inputs']:
                    if isinstance(v['inputs']['seed_num'], int):
                        v['inputs']['seed_num'] = seed_generator.next()

                if 'seed' in v['inputs']:
                    if isinstance(v['inputs']['seed'], int):
                        v['inputs']['seed'] = seed_generator.next()

                if 'noise_seed' in v['inputs']:
                    if isinstance(v['inputs']['noise_seed'], int):
                        v['inputs']['noise_seed'] = seed_generator.next()

                for k2, v2 in v['inputs'].items():
                    if isinstance(v2, str) and '$GlobalSeed.value$' in v2:
                        v['inputs'][k2] = v2.replace('$GlobalSeed.value$', str(value))
        # control after generated
        if mode is not None and not mode:
            control_seed(node[1], action, seed_is_global)

    return value is not None


def workflow_seed_update(json_data):
    nodes = json_data['extra_data']['extra_pnginfo']['workflow']['nodes']
    seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    prompt = json_data['prompt']

    updated_seed_map = {}
    value = None

    for node in nodes:
        node_id = str(node['id'])
        if node_id in prompt:
            if node['type'] == 'Simple Seed Selector TnT':
                print(prompt[node_id])
                value = prompt[node_id]['inputs']['seed_value']
                length = len(node['widgets_values'])
                node['widgets_values'][length-1] = node['widgets_values'][0]
                node['widgets_values'][0] = value
            elif node_id in seed_widget_map:
                widget_idx = seed_widget_map[node_id]

                if 'seed_num' in prompt[node_id]['inputs']:
                    seed = prompt[node_id]['inputs']['seed_num']
                elif 'noise_seed' in prompt[node_id]['inputs']:
                    seed = prompt[node_id]['inputs']['noise_seed']
                else:
                    seed = prompt[node_id]['inputs']['seed']

                node['widgets_values'][widget_idx] = seed
                updated_seed_map[node_id] = seed

    server.PromptServer.instance.send_sync("ShowPrompt", {"id": node_id, "value": value, "seed_map": updated_seed_map})


def set_seed_values(json_data, global_seed_node_id, new_seed):
    seed_widget_map = json_data['extra_data']['extra_pnginfo']['workflow']['seed_widgets']
    wf_nodes = json_data['extra_data']['extra_pnginfo']['workflow']['nodes']
    prompt = json_data['prompt']
    
    input_names = ["seed", "noise_seed", "seed_num"]
    for k, v in seed_widget_map.items():
        input = ''
        for input_name in input_names:
            if prompt.get(k).get('inputs').get(input_name) != None:
                input = input_name
                break
            
        prompt[k]['inputs'][input] = new_seed


def onprompt(json_data):
    new_seed = random.randint(0, MAX_SEED_NUM)
    #"Simple Seed Selector TnT"
    global_seed_node_id, global_enabled, fixed_seed_enabled = has_global_seed_node(json_data)
    # is_changed = prompt_seed_update(json_data)
    if global_seed_node_id != -1:
        set_seed_values(json_data, global_seed_node_id, new_seed)
        workflow_seed_update(json_data)
    
    return json_data

server.PromptServer.instance.add_on_prompt_handler(onprompt)


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
                "seed_value": ("INT", {"default": 1, "min": 1, "max": MAX_SEED_NUM}),
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

    def run(self, seed_value, mode, global_seed, **kwargs):
        print("run")
        # Force update
        def IS_CHANGED(self):
            print("IS_CHANGED")
            self.num += 1 if self.num == 0 else -1
            return self.num
        setattr(self.__class__, 'IS_CHANGED', IS_CHANGED)

        return (int(seed_value), float(seed_value))
    
    
NODE_CLASS_MAPPINGS = {
    "Simple Seed Selector (Hapse)": SimpleSeedSelector,
}