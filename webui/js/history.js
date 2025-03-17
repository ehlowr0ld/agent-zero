import { getContext } from "../index.js";

export async function openHistoryModal() {
    try {
        const hist = await window.sendJsonData("/history_get", { context: getContext() });
        const data = JSON.stringify(hist.history, null, 4);
        const size = hist.tokens
        await showEditorModal(data, "json", `History ~${size} tokens`, "Conversation history visible to the LLM. History is compressed to fit into the context window over time.");
    } catch (e) {
        window.toastFetchError("Error fetching history", e)
        return
    }
}

export async function openCtxWindowModal() {
    try {
        const win = await window.sendJsonData("/ctx_window_get", { context: getContext() });
        const data = win.content
        const size = win.tokens
        await showEditorModal(data, "markdown", `Context window ~${size} tokens`, "Data passed to the LLM during last interaction. Contains system message, conversation history and RAG.");
    } catch (e) {
        window.toastFetchError("Error fetching context", e)
        return
    }
}

export async function openTaskListModal() {
    try {
        const taskList = await window.sendJsonData("/tasklist_get", { context: getContext() });
        const data = JSON.stringify(taskList.content, null, 4);
        const size = taskList.tokens
        await showEditorModal(data, "json", `Task List ~${size} tokens`, "Task list for the current context.");
    } catch (e) {
        window.toastFetchError("Error fetching task list", e)
        return
    }
}

export async function openNotepadModal() {
    try {
        const notepad = await window.sendJsonData("/notepad_get", { context: getContext() });
        const data = JSON.stringify(notepad.content, null, 4);
        const size = notepad.tokens
        await showEditorModal(data, "json", `Notepad ~${size} tokens`, "Notepad for the current context.");
    } catch (e) {
        window.toastFetchError("Error fetching notepad", e)
        return
    }
}

async function showEditorModal(data, type = "json", title, description = "") {
    // Generate the HTML with JSON Viewer container
    const html = `<div id="json-viewer-container"></div>`;

    // Open the modal with the generated HTML
    await window.genericModalProxy.openModal(title, description, html, ["history-viewer"]);

    // Initialize the JSON Viewer after the modal is rendered
    const container = document.getElementById("json-viewer-container");
    if (container) {
        const editor = ace.edit("json-viewer-container");

        const dark = localStorage.getItem('darkMode')
        if (dark != "false") {
            editor.setTheme("ace/theme/github_dark");
        } else {
            editor.setTheme("ace/theme/tomorrow");
        }

        editor.session.setMode("ace/mode/" + type);
        editor.setValue(data);
        editor.clearSelection();
        // editor.session.$toggleFoldWidget(5, {})
    }
}

window.openHistoryModal = openHistoryModal;
window.openCtxWindowModal = openCtxWindowModal;
window.openTaskListModal = openTaskListModal;
window.openNotepadModal = openNotepadModal;
