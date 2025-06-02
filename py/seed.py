import random
import server

# credits for base concept goes to inspire https://github.com/ltdrdata/ComfyUI-Inspire-Pack

MAX_SEED_NUM = 1125899906842624

# The class type string that ComfyUI uses for the SimpleSeedSelector node,
# typically derived from NODE_CLASS_MAPPINGS.
# Based on this file's mapping and seed_old.py, this is the most likely name.
# If the main __init__.py for the custom node package renames it, this constant would need to reflect that.
SSS_CLASS_TYPE = "Simple Seed Selector TnT"


def _propagate_seed_value(prompt_data, workflow_nodes_data, seed_widget_map, new_seed_value, controlling_node_id_str=None, sss_class_type_to_skip=None, ignored_node_ids_set=None):
    """
    Updates seed inputs in the prompt and corresponding widget values in the workflow.
    - prompt_data: The 'prompt' part of the JSON (execution graph).
    - workflow_nodes_data: The 'nodes' list from 'extra_pnginfo.workflow' (UI graph).
    - seed_widget_map: Maps node_id (str) to seed widget_index (int) for UI updates.
    - new_seed_value: The integer seed value to apply.
    - controlling_node_id_str: The string ID of the SimpleSeedSelector node.
    - sss_class_type_to_skip: The class type of the SimpleSeedSelector node, to avoid self-modification of standard seed inputs.
    - ignored_node_ids_set: A set of node IDs (strings) that should not have their seeds updated.
    """
    standard_seed_input_names = ["seed", "noise_seed", "seed_num"]
    updated_widgets_for_sync = {} # Collect updates for send_sync

    for node_id_str_loop, node_content in prompt_data.items():
        node_inputs = node_content.get("inputs", {})
        class_type = node_content.get("class_type", "")

        # Skip if this node ID is in the ignored list
        if ignored_node_ids_set and node_id_str_loop in ignored_node_ids_set:
            # print(f"Node {node_id_str_loop} ('{class_type}') is in ignore_node_id list. Skipping seed propagation.")
            continue

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
                        # print(f"Node {node_id_str_loop} ('{class_type}'): Updating '{seed_name}' from '{current_value}' to {new_seed_value}")
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
                                        updated_widgets_for_sync[node_id_str_loop] = int(new_seed_value)
                                    else:
                                        print(f"  Warning: Widget index {widget_idx} for node {node_id_str_loop} out of bounds or invalid widget_values.")
                                # else:
                                #     print(f"  Note: Node {node_id_str_loop} ('{class_type}') prompt input '{seed_name}' updated. Not in seed_widget_map, so UI widget might not reflect this change.")
                                break # Found the workflow node for UI update
                            
    return updated_widgets_for_sync


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
    sss_ignore_node_id_str = ""
    
    sync_payload = {"sss_update": None, "propagated_updates": {}}
    
    # Iterate through prompt to find the SimpleSeedSelector node
    for node_id_str, node_content in prompt.items():
        if node_content.get('class_type') == SSS_CLASS_TYPE:
            controlling_sss_node_id_str = node_id_str
            inputs = node_content.get('inputs', {})
            sss_seed_value_from_input = inputs.get('seed_value')
            sss_is_fixed_mode = inputs.get('mode', True) # True for "fixed_seed"
            sss_is_global_enabled = inputs.get('global_seed', False)
            sss_ignore_node_id_str = inputs.get('ignore_node_id', "")
            # print(f"Found {SSS_CLASS_TYPE} (Node ID: {controlling_sss_node_id_str}): seed_value_input={sss_seed_value_from_input}, mode_fixed={sss_is_fixed_mode}, global_enabled={sss_is_global_enabled}")
            break 

    if controlling_sss_node_id_str:
        # Initialize seed_for_sss_node with the current input value from the SSS node.
        # This value might be an int if directly set, or already resolved by ComfyUI if linked.
        seed_for_sss_node = None
        if isinstance(sss_seed_value_from_input, (int, float)):
            seed_for_sss_node = int(sss_seed_value_from_input)
        # else: sss_seed_value_from_input might be invalid or not yet resolved to a number.

        # If SSS node is in "randomize_seed" mode, generate a new seed for it.
        # This happens regardless of the global_seed setting.
        if not sss_is_fixed_mode: # False means "randomize_seed"
            new_random_seed = random.randint(0, MAX_SEED_NUM)
            # print(f"SSS Node {controlling_sss_node_id_str} is in RANDOMIZE mode. Generated new seed: {new_random_seed}")
            seed_for_sss_node = new_random_seed # This is the value the SSS node will now have
            
            # Update the SSS node's 'seed_value' input in the prompt data
            if controlling_sss_node_id_str in prompt and 'inputs' in prompt[controlling_sss_node_id_str]:
                prompt[controlling_sss_node_id_str]['inputs']['seed_value'] = seed_for_sss_node
            
            # Update the SSS node's widget value in the workflow_nodes data (for UI)
            for wf_node in workflow_nodes:
                if str(wf_node.get('id')) == controlling_sss_node_id_str:
                    if 'widgets_values' in wf_node and isinstance(wf_node['widgets_values'], list) and len(wf_node['widgets_values']) > 0:
                        # 'seed_value' is assumed to be the first widget based on INPUT_TYPES order
                        wf_node['widgets_values'][0] = seed_for_sss_node 
                        # print(f"  Updated UI widget for {SSS_CLASS_TYPE} (Node {controlling_sss_node_id_str}) to {seed_for_sss_node}")
                        sync_payload["sss_update"] = {
                            "node_id": controlling_sss_node_id_str,
                            "new_value": seed_for_sss_node
                        }
                    else:
                        print(f"  Warning: Could not update UI widget for {SSS_CLASS_TYPE} (Node {controlling_sss_node_id_str}). Missing or invalid 'widgets_values'.")
                    break
        # else: SSS is in "fixed_seed" mode. seed_for_sss_node remains its input value (or None if input was initially invalid).

        # Now, if global_seed is enabled AND we have a valid seed from/for the SSS node, propagate it.
        if sss_is_global_enabled:
            if seed_for_sss_node is not None: # Ensure we have a valid integer seed
                # print(f"Global seed is ENABLED for Node {controlling_sss_node_id_str}. Propagating seed: {seed_for_sss_node}")
                
                ignored_node_ids_set = set()
                if sss_ignore_node_id_str and isinstance(sss_ignore_node_id_str, str):
                    ignored_node_ids_set = {node_id.strip() for node_id in sss_ignore_node_id_str.split(',') if node_id.strip()}
                
                propagated_widget_updates = _propagate_seed_value(
                    prompt, 
                    workflow_nodes, 
                    seed_widget_map, 
                    seed_for_sss_node, # Use the (potentially newly randomized) seed of the SSS node
                    controlling_sss_node_id_str, 
                    SSS_CLASS_TYPE, 
                    ignored_node_ids_set
                )
                if propagated_widget_updates:
                    sync_payload["propagated_updates"] = propagated_widget_updates
            else:
                # This case could happen if SSS is in fixed mode but its input 'seed_value' was not a valid number.
                print(f"Warning: {SSS_CLASS_TYPE} (Node {controlling_sss_node_id_str}) has global_seed enabled, but its own seed_value is invalid ({sss_seed_value_from_input}). Skipping global seed propagation.")
        # else:
            # if not sss_is_global_enabled:
                # print(f"Global seed is DISABLED for Node {controlling_sss_node_id_str}. Seed {seed_for_sss_node} (if any) will not be propagated.")
        
    # Send updates to client if any occurred
    if sync_payload["sss_update"] or sync_payload["propagated_updates"]:
        # print(f"Sending UI update to client: {sync_payload}")
        server.PromptServer.instance.send_sync("tnt_global_seed_update", sync_payload)
    
    
    return json_data

server.PromptServer.instance.add_on_prompt_handler(onprompt)

# SimpleSeedSelector
class SimpleSeedSelector:
    change_tracker_cls = 0 # Class attribute for IS_CHANGED
    # No __init__ needed if it only contains change_tracker for IS_CHANGED
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed_value": ("INT", {"default": 1, "min": 1, "max": MAX_SEED_NUM, "tooltip": "The seed to use, max is 1125899906842624"}),
                "ignore_node_id": ("STRING", {"default": "", "tooltip": "Comma-separated list of node IDs to skip even when global_seed is enabled"}),
                "global_seed": ("BOOLEAN", {"default": True, "tooltip": "Should it affect all nodes that contains seed/noise_seed/seed_num"}),
                "mode": ("BOOLEAN", {"default": True, "label_on": "fixed_seed", "label_off": "randomize_seed", "tooltip": "Fixed or random seed"}), # True = fixed
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed_int",)
    FUNCTION = "run"
    CATEGORY = "utils/this_and_that"
    OUTPUT_NODE = True

    def run(self, seed_value, ignore_node_id, global_seed, mode, **kwargs): # Hidden inputs are in kwargs
        # The seed_value passed here is the one from the prompt,
        # which might have been updated by the onprompt handler if global_seed is active and mode is randomize.
        # print(f"SimpleSeedSelector RUN: seed_value={seed_value}, mode_fixed={mode}, global_enabled={global_seed}")    
        return (int(seed_value),)
    
    @classmethod
    def IS_CHANGED(cls, seed_value, mode, global_seed, **kwargs): # Now a class method
        # Toggle a class-level value to signify change
        cls.change_tracker_cls = 1 - cls.change_tracker_cls 
        return float(cls.change_tracker_cls)
    
NODE_CLASS_MAPPINGS = {
    "Simple Seed Selector TnT": SimpleSeedSelector,
}