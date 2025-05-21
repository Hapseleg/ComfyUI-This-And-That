import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

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

// function overwriteSeedControl(nodeType) {
//     const onNodeCreated = nodeType.prototype.onNodeCreated;
//     nodeType.prototype.onNodeCreated = function () {
//         onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
//         this.seedControl = new SeedControl(this);
//     }
// }

console.log("---")
app.registerExtension({
    name: "comfy.ttN.widgets",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // if (nodeData.name.startsWith("ttN ") && ["ttN pipeLoader_v2", "ttN pipeKSampler_v2", "ttN pipeKSamplerAdvanced_v2", "ttN pipeLoaderSDXL_v2", "ttN pipeKSamplerSDXL_v2", "ttN KSampler_v2"].includes(nodeData.name)) {
        if (nodeData.output_name.includes('seed')) {
            overwriteSeedControl(nodeType)
        }
        // }
        console.log(nodeData)
        console.log(nodeType)
        if (["ttN_textDebug","Show Prompt (Hapse)"].includes(nodeData.name)) {
            addTextDisplay(nodeType)
        }
        // if (nodeData.name.startsWith("ttN textCycle")) {
        //     overwriteIndexControl(nodeType)
        // }
    },
}); 