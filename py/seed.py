import random
import server
# from enum import Enum # Not used by new logic

MAX_SEED_NUM = 18446744073709552000

# SGmode and SeedGenerator are not used by the new SimpleSeedSelector logic.
# class SGmode(Enum):
# ...
# class SeedGenerator:
# ...

# The class type string that ComfyUI uses for the SimpleSeedSelector node,
# typically derived from NODE_CLASS_MAPPINGS.
# Based on this file's mapping and seed_old.py, this is the most likely name.
# If the main __init__.py for the custom node package renames it, this constant would need to reflect that.
SSS_CLASS_TYPE = "Simple Seed Selector TnT"


def _propagate_seed_value(prompt_data, workflow_nodes_data, seed_widget_map, new_seed_value, controlling_node_id_str=None, sss_class_type_to_skip=None):
    """
    Updates seed inputs in the prompt and corresponding widget values in the workflow.
    - prompt_data: The 'prompt' part of the JSON (execution graph).
    - workflow_nodes_data: The 'nodes' list from 'extra_pnginfo.workflow' (UI graph).
    - seed_widget_map: Maps node_id (str) to seed widget_index (int) for UI updates.
    - new_seed_value: The integer seed value to apply.
    - controlling_node_id_str: The string ID of the SimpleSeedSelector node.
    - sss_class_type_to_skip: The class type of the SimpleSeedSelector node, to avoid self-modification of standard seed inputs.
    """
    standard_seed_input_names = ["seed", "noise_seed", "seed_num"]

    for node_id_str_loop, node_content in prompt_data.items():
        node_inputs = node_content.get("inputs", {})
        class_type = node_content.get("class_type", "")

        # Skip applying standard seed logic to the controlling SimpleSeedSelector itself
        if sss_class_type_to_skip and node_id_str_loop == controlling_node_id_str and class_type == sss_class_type_to_skip:
            # Its 'seed_value' input (if randomized) and widget are handled in 'onprompt'
            continue 

        # For all other nodes:
        for seed_name in standard_seed_input_names:
            if seed_name in node_inputs:
                current_value = node_inputs[seed_name]
                # Check if current_value is a direct number or a link from the controlling SSS node
                is_link_from_controller = (isinstance(current_value, list) and
                                           len(current_value) == 2 and
                                           controlling_node_id_str is not None and # Ensure controller exists
                                           str(current_value[0]) == controlling_node_id_str)

                if isinstance(current_value, (int, float)) or is_link_from_controller:
                    # Update if different or if it was a link that needs to be replaced by a concrete value
                    if node_inputs[seed_name] != int(new_seed_value) or is_link_from_controller:
                        print(f"Node {node_id_str_loop} ('{class_type}'): Updating '{seed_name}' from '{current_value}' to {new_seed_value}")
                        node_inputs[seed_name] = int(new_seed_value)

                        # Update corresponding widget in workflow_nodes_data for UI
                        for wf_node in workflow_nodes_data:
                            if str(wf_node.get('id')) == node_id_str_loop:
                                if node_id_str_loop in seed_widget_map:
                                    widget_idx = seed_widget_map[node_id_str_loop]
                                    if 'widgets_values' in wf_node and \
                                       isinstance(wf_node['widgets_values'], list) and \
                                       widget_idx < len(wf_node['widgets_values']):
                                        wf_node['widgets_values'][widget_idx] = int(new_seed_value)
                                    else:
                                        print(f"  Warning: Widget index {widget_idx} for node {node_id_str_loop} out of bounds or invalid widget_values.")
                                # else:
                                #     print(f"  Note: Node {node_id_str_loop} ('{class_type}') prompt input '{seed_name}' updated. Not in seed_widget_map, so UI widget might not reflect this change.")
                                break # Found the workflow node for UI update


def onprompt(json_data):
    prompt = json_data.get('prompt', {})
    extra_pnginfo = json_data.get('extra_data', {}).get('extra_pnginfo', {})
    workflow = extra_pnginfo.get('workflow', {})
    workflow_nodes = workflow.get('nodes', []) # For UI widget updates
    
    seed_widget_map = workflow.get('seed_widgets', {})
    if not isinstance(seed_widget_map, dict):
        print(f"Warning: 'seed_widgets' is not a dictionary (type: {type(seed_widget_map)}). Global seed UI updates might fail.")
        seed_widget_map = {}

    controlling_sss_node_id_str = None
    sss_seed_value_from_input = None
    sss_is_fixed_mode = True 
    sss_is_global_enabled = False
    
    for node_id_str, node_content in prompt.items():
        if node_content.get('class_type') == SSS_CLASS_TYPE:
            controlling_sss_node_id_str = node_id_str
            inputs = node_content.get('inputs', {})
            sss_seed_value_from_input = inputs.get('seed_value')
            sss_is_fixed_mode = inputs.get('mode', True) # True for "fixed_seed"
            sss_is_global_enabled = inputs.get('global_seed', False)
            print(f"Found {SSS_CLASS_TYPE} (Node ID: {controlling_sss_node_id_str}): seed_value_input={sss_seed_value_from_input}, mode_fixed={sss_is_fixed_mode}, global_enabled={sss_is_global_enabled}")
            break 

    if controlling_sss_node_id_str and sss_is_global_enabled:
        target_seed = -1

        if sss_is_fixed_mode:
            if isinstance(sss_seed_value_from_input, (int, float)):
                target_seed = int(sss_seed_value_from_input)
                print(f"Global seed (FIXED) from Node {controlling_sss_node_id_str}: {target_seed}")
            else:
                print(f"Warning: {SSS_CLASS_TYPE} (Node {controlling_sss_node_id_str}) is in fixed mode but seed_value is not a number: {sss_seed_value_from_input}. Skipping global seed propagation.")
                return json_data 
        else: # Randomize mode
            target_seed = random.randint(0, MAX_SEED_NUM)
            print(f"Global seed (RANDOM) from Node {controlling_sss_node_id_str}: {target_seed}. Updating this node's own seed_value.")
            
            if controlling_sss_node_id_str in prompt and 'inputs' in prompt[controlling_sss_node_id_str]:
                prompt[controlling_sss_node_id_str]['inputs']['seed_value'] = target_seed
            
            for wf_node in workflow_nodes:
                if str(wf_node.get('id')) == controlling_sss_node_id_str:
                    if 'widgets_values' in wf_node and isinstance(wf_node['widgets_values'], list) and len(wf_node['widgets_values']) > 0:
                        wf_node['widgets_values'][0] = target_seed # 'seed_value' is the first widget
                        print(f"  Updated UI widget for {SSS_CLASS_TYPE} (Node {controlling_sss_node_id_str}) to {target_seed}")
                    else:
                        print(f"  Warning: Could not update UI widget for {SSS_CLASS_TYPE} (Node {controlling_sss_node_id_str}). Missing or invalid 'widgets_values'.")
                    break
        
        if target_seed != -1:
            print(f"Propagating global seed: {target_seed} to other nodes.")
            _propagate_seed_value(prompt, workflow_nodes, seed_widget_map, target_seed, controlling_sss_node_id_str, SSS_CLASS_TYPE)

    return json_data

server.PromptServer.instance.add_on_prompt_handler(onprompt)

# SimpleSeedSelector
class SimpleSeedSelector:
    def __init__(self):
        self.change_tracker = 0 # For IS_CHANGED
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed_value": ("INT", {"default": 1, "min": 1, "max": MAX_SEED_NUM}),
                "mode": ("BOOLEAN", {"default": True, "label_on": "fixed_seed", "label_off": "randomize_seed"}), # True = fixed
                "global_seed": ("BOOLEAN", {"default": True, "label_on": "global_active", "label_off": "global_inactive"}),
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

    def run(self, seed_value, mode, global_seed, **kwargs): # Hidden inputs are in kwargs
        # The seed_value passed here is the one from the prompt,
        # which might have been updated by the onprompt handler if global_seed is active and mode is randomize.
        # print(f"SimpleSeedSelector RUN: seed_value={seed_value}, mode_fixed={mode}, global_enabled={global_seed}")
        return (int(seed_value), float(seed_value))
    
    # This method is called by ComfyUI with the widget values.
    def IS_CHANGED(self, seed_value, mode, global_seed, **kwargs):
        # Toggle a value to signify change, ensuring the node can be re-evaluated if interacted with.
        self.change_tracker = 1 - self.change_tracker 
        return float(self.change_tracker)
    
NODE_CLASS_MAPPINGS = {
    "Simple Seed Selector TnT": SimpleSeedSelector, # This name might be overridden by __init__.py
}