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
