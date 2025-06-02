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
        // If "Simple Seed Selector TnT" (or its registered name) needs specific JS on creation,
        // it can be added here. Currently, no specific JS is added for it on node creation.
        // Example: if (nodeData.name === "Simple Seed Selector TnT") { /* ... */ }
    },
}); 

// The api.addEventListener("TnT-SimpleSeedSelector", ...) has been removed.
// The Python 'onprompt' handler now directly modifies widget values in the workflow data
// sent to the backend, which ComfyUI uses for UI updates. This event listener
// is likely obsolete for the current seed propagation mechanism and used incorrect widget names.

// Save original queuePrompt function
const originalQueuePrompt = api.queuePrompt;

// Override queuePrompt to collect seed widgets
api.queuePrompt = async function (e, { output: op, workflow: wf }) {
    console.log("TnT Custom Node: Overriding queuePrompt to collect seed widget information.");

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
                    if (widget && (widget.name === "seed" || widget.name === "noise_seed" || widget.name === "seed_num") && widget.type !== "converted-widget") {
                        wf.seed_widgets[nodeId] = i; // Store the numeric index
                        break; // Found the primary seed widget for this node
                    }
                }
            }
        }
    } else {
        console.warn("TnT Custom Node: app.graph or app.graph._nodes_by_id is undefined. Cannot collect seed_widgets.");
    }
    console.log("TnT Custom Node: Collected seed_widgets map:", wf.seed_widgets);

    return await originalQueuePrompt.call(api, e, { output: op, workflow: wf });
}