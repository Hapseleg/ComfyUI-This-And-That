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
        if (["Simple Seed Selector (Hapse)"].includes(nodeData.name)) {
            
        }
    },
}); 


api.addEventListener("TnT-SimpleSeedSelector", function (e) {
    console.log("addEventListener")
    console.log(e)
    let nodes = app.graph._nodes_by_id;
    for (let nodeId in nodes) {
        console.log("hereW")
        let node = nodes[nodeId];
        console.log(node)
        // If node is the global seed node
        if (node.type === "Simple Seed Selector TnT") {
            if (node.widgets) {
                const valueWidget = node.widgets.find(w => w.name === "value");
                const lastSeedWidget = node.widgets.find(w => w.name === "last_seed");
                if (lastSeedWidget && valueWidget) {
                    lastSeedWidget.value = valueWidget.value;
                    valueWidget.value = e.detail.value;
                }
            }
        } else if (node.widgets) {
            // For other nodes, update seed-related widgets if present
            const seedWidget = node.widgets.find(
                w => w.name === "seed_num" || w.name === "seed" || w.name === "noise_seed"
            );
            if (seedWidget && e.detail.seed_map[node.id] != null) {
                seedWidget.value = e.detail.seed_map[node.id];
            }
        }
    }
})

// Save original queuePrompt function
const originalQueuePrompt = api.queuePrompt;

// Override queuePrompt to collect seed widgets
api.queuePrompt = async function (e, { output: op, workflow: wf }) {
    console.log("queuePrompt")
    let seedNodeId = null
    let seedNodeFixedEnabled = false
    let seedNodeGlobalEnabled = false
    wf['nodes'].forEach(n => {
        if (n['type'] == "Simple Seed Selector TnT"){
            seedNodeId = n['id']
            seedNodeFixedEnabled = n['widgets_values'][1]
            seedNodeGlobalEnabled = n['widgets_values'][2]
        }
    });

    
    if(seedNodeId != null){
        wf.global_seed_widget_id = seedNodeId;
        wf.global_seed_widget_fixed_enabled = seedNodeFixedEnabled;
        wf.global_seed_widget_global_enabled = seedNodeGlobalEnabled;
        // wf.global_seed_widget_id = {};
        // wf.global_seed_widget_id[seedNodeId] = seedNodeGlobalEnabled


        wf.seed_widgets = {};
        for (let nodeId in app.graph._nodes_by_id) {
            let widgets = app.graph._nodes_by_id[nodeId].widgets;
            if (widgets) {
                for (let idx in widgets) {
                    let widget = widgets[idx];
                    if ((widget.name === "seed_num" || widget.name === "seed" || widget.name === "noise_seed") && widget.type !== "converted-widget") 
                        wf.seed_widgets[nodeId] = parseInt(idx);
                    
                }
            }
        }
    }

    

    return await originalQueuePrompt.call(api, e, { output: op, workflow: wf });
}