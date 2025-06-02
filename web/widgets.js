import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// From https://github.com/TinyTerra/ComfyUI_tinyterraNodes
function addTextDisplay(nodeType) {
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        const r = onNodeCreated?.apply(this, arguments);
        const w = ComfyWidgets["STRING"](this, "display", ["STRING", { multiline: true, placeholder: " " }], app).widget;
        w.inputEl.readOnly = true;
        w.inputEl.style.opacity = 0.7;
        w.inputEl.style.cursor = "auto";
        return r;
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments);

        for (const widget of this.widgets) {
            if (widget.type === "customtext" && widget.name === "display" && widget.inputEl.readOnly === true) {
                widget.value = message.text.join('');
            }
        }
        this.onResize?.(this.size);
    };
}

app.registerExtension({
    name: "thisNthat.widgets",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (["Show Prompt (Hapse)"].includes(nodeData.name)) {
            addTextDisplay(nodeType)
        }
    },
}); 

api.addEventListener("tnt_global_seed_update", function(event) { // event here is from addEventListener
    // console.log("TnT: Received tnt_global_seed_update event:", event);
    const payload = event.detail; // Data from send_sync is in event.detail

    if (!payload) {
        console.error("TnT: Received tnt_global_seed_update but payload (event.detail) is missing or undefined.", event);
        return;
    }

    const graph = app.graph; // Get the current graph
    let needsRedraw = false;

    // Handle update for the SimpleSeedSelector node itself
    if (payload.sss_update && payload.sss_update.node_id) {
        const sssNode = graph.getNodeById(parseInt(payload.sss_update.node_id));
        if (sssNode && sssNode.widgets) {
            // Find the 'seed_value' widget. It's usually the first one.
            const seedValueWidget = sssNode.widgets.find(w => w.name === "seed_value") || sssNode.widgets[0];
            if (seedValueWidget) {
                // console.log(`TnT: Updating SSS Node ${payload.sss_update.node_id} widget '${seedValueWidget.name}' to ${payload.sss_update.new_value}`);
                seedValueWidget.value = payload.sss_update.new_value;

                // It's good practice to also call the widget's callback if it exists,
                // though for simple value display, it might not be strictly necessary.
                // The index for the callback might need to be found if not always 0.
                const widgetIndex = sssNode.widgets.indexOf(seedValueWidget);
                if (seedValueWidget.callback && widgetIndex !== -1) {
                    seedValueWidget.callback(payload.sss_update.new_value, sssNode, widgetIndex, {});
                }
                sssNode.setDirtyCanvas(true, true); // Mark for redraw
                needsRedraw = true;
            }
        }
    }

    // Handle propagated updates for other nodes
    if (payload.propagated_updates) {
        for (const nodeIdStr in payload.propagated_updates) {
            const newValue = payload.propagated_updates[nodeIdStr];
            const node = graph.getNodeById(parseInt(nodeIdStr));
            
            if (node && node.widgets) {
                // Find a seed-related widget by common names directly
                const seedWidgetToUpdate = node.widgets.find(w => 
                    (w.name === "seed" || w.name === "noise_seed" || w.name === "seed_num") && 
                    w.type !== "converted-widget" // Ensure it's a native widget we can set .value on
                );

                if (seedWidgetToUpdate) {
                    // console.log(`TnT: Updating Node ${nodeIdStr} widget '${seedWidgetToUpdate.name}' to ${newValue}`);
                    seedWidgetToUpdate.value = newValue;
                    const widgetIndex = node.widgets.indexOf(seedWidgetToUpdate);
                    if (seedWidgetToUpdate.callback && widgetIndex !== -1) {
                        seedWidgetToUpdate.callback(newValue, node, widgetIndex, {});
                    }
                    node.setDirtyCanvas(true, true); // Mark for redraw
                    needsRedraw = true;
                } else {
                    // This warning is fine, as not all nodes will have a seed widget we can/should update.
                    // console.warn(`TnT: No standard seed widget (seed, noise_seed, seed_num) found for node ID ${nodeIdStr} to update with value ${newValue}`);
                }
            }
        }
    }

    if(needsRedraw) {
        app.graph.setDirtyCanvas(true, true); // Redraw the whole graph if any changes were made
    }
});

// Save original queuePrompt function
const originalQueuePrompt = api.queuePrompt;

// Override queuePrompt to collect seed widgets
api.queuePrompt = async function (e, { output: op, workflow: wf }) {
    // console.log("TnT Custom Node: Overriding queuePrompt to collect seed widget information.");

    // The Python 'onprompt' handler identifies the SimpleSeedSelector TnT node
    // and its settings (mode, global_seed) directly from the 'prompt' (execution graph) data.
    // Therefore, explicitly passing this info via 'wf.global_seed_widget' is not strictly necessary
    // for the Python side to get those settings.

    // This part IS CRUCIAL for the Python backend to update UI widgets of OTHER nodes.
    wf.seed_widgets = {}; // Maps nodeId to the index of its seed widget
    if (app.graph && app.graph._nodes_by_id) {
        for (const nodeId in app.graph._nodes_by_id) {
            const node = app.graph._nodes_by_id[nodeId];
            if (node && Array.isArray(node.widgets)) {
                for (let i = 0; i < node.widgets.length; i++) {
                    const widget = node.widgets[i];
                    if (widget && (widget.name === "seed" || widget.name === "noise_seed" || widget.name === "seed_num" || widget.name === "seed_value") && widget.type !== "converted-widget") {
                        wf.seed_widgets[nodeId] = i; // Store the numeric index
                        break; // Found the primary seed widget for this node
                    }
                }
            }
        }
    } else {
        console.warn("TnT Custom Node: app.graph or app.graph._nodes_by_id is undefined. Cannot collect seed_widgets.");
    }
    // console.log("TnT Custom Node: Collected seed_widgets map:", wf.seed_widgets);

    return await originalQueuePrompt.call(api, e, { output: op, workflow: wf });
}
