/**
 * simulator.js — Interactive PyDevices Python Simulator Engine
 *
 * Manages the Monaco editor and its multi-file program buffers, the xterm
 * REPL over the MicroPython WebAssembly runtime, locally saved programs,
 * and the resizable split layout.
 */

(function () {
  const MONACO_BASE = "/vendor/monaco/";

  let monacoEditor = null;
  let currentResolution = { width: 320, height: 240, shape: "rectangle" };
  // A display the program has already built keeps the size it booted with, so a
  // resolution change only needs the "Reset VM" nudge once something has run.
  let hasRunSinceBoot = false;

  // DOM Elements
  const elStatusDot = document.getElementById("status-dot");
  const elStatusText = document.getElementById("status-text");
  const elTemplateSelect = document.getElementById("template-select");
  const elResolutionSelect = document.getElementById("resolution-select");
  const elRunBtn = document.getElementById("run-btn");
  const elResetVmBtn = document.getElementById("reset-vm");
  const elStopBtn = document.getElementById("stop-btn");
  const elProgramBtn = document.getElementById("program-btn");
  const elClearConsoleBtn = document.getElementById("clear-console-btn");
  const elDeviceBezel = document.getElementById("device-bezel");
  const elCanvas = document.getElementById("display_canvas");
  const elToast = document.getElementById("sim-toast");


  // =========================================================================
  // Status & Console Helpers
  // =========================================================================

  function setStatus(text, state = "ready") {
    if (elStatusText) elStatusText.textContent = text;
    if (elStatusDot) {
      elStatusDot.className = "sim-status-dot";
      if (state === "ready") elStatusDot.classList.add("is-ready");
      else if (state === "busy") elStatusDot.classList.add("is-busy");
      else if (state === "error") elStatusDot.classList.add("is-error");
    }
  }

  function clearConsole() {
    if (window.__pydevicesTerminal) window.__pydevicesTerminal.clear();
  }

  function showToast(msg) {
    if (!elToast) return;
    elToast.textContent = msg;
    elToast.classList.add("is-active");
    setTimeout(() => elToast.classList.remove("is-active"), 2600);
  }

  function isInstalledPwa() {
    return window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true;
  }

  function showInstallHint() {
    const hint = document.getElementById("install-hint");
    if (hint && !isInstalledPwa() && sessionStorage.getItem("sim-install-hint-dismissed") !== "1") {
      hint.hidden = false;
    }
  }

  // These live in the overflow menu as icon + label, so relabel the span rather
  // than the button -- textContent on the button would drop the icon.
  function setButtonLabel(button, text) {
    if (!button) return;
    const label = button.querySelector("span");
    if (label) label.textContent = text;
    else button.textContent = text;
  }

  async function refreshApplication() {
    const button = document.getElementById("refresh-application");
    if (button) {
      button.disabled = true;
      setButtonLabel(button, "Refreshing…");
    }
    persistState();
    try {
      if ("caches" in window) {
        const names = await caches.keys();
        await Promise.all(names
          .filter((name) => name.startsWith("pydevices-simulator-"))
          .map((name) => caches.delete(name)));
      }
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        const simulatorScope = new URL("./", location.href).href;
        await Promise.all(registrations
          .filter((registration) => registration.scope === simulatorScope)
          .map((registration) => registration.unregister()));
      }
    } finally {
      const url = new URL(location.href);
      url.searchParams.set("app-refresh", Date.now().toString());
      location.replace(url.href);
    }
  }

  // =========================================================================
  // Program Files
  // =========================================================================
  //
  // A program is a flat set of .py files sharing one working directory, with
  // main.py as the entry point. Flat is deliberate: the runtime already has "."
  // on sys.path, so `import helper` resolves with no packaging ceremony -- and
  // it keeps a file name and a module name the same thing.

  const ENTRY_FILE = "main.py";
  const DRAFT_STORAGE_KEY = "pydevices-simulator-draft";
  const LEGACY_CODE_KEY = "pydevices-simulator-code";
  const FILE_NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*\.py$/;

  // name -> monaco model. Insertion order is tab order, with the entry pinned
  // first by loadFiles().
  const fileModels = new Map();
  let activeFile = ENTRY_FILE;

  function fileSource(name) {
    const model = fileModels.get(name);
    return model ? model.getValue() : "";
  }

  function allFiles() {
    const out = {};
    for (const name of fileModels.keys()) out[name] = fileSource(name);
    return out;
  }

  function entrySource() {
    return fileSource(ENTRY_FILE);
  }

  function makeModel(name, source) {
    return monaco.editor.createModel(source, "python", monaco.Uri.file("/" + name));
  }

  // Replaces the whole file set -- used at boot, on template change, and when a
  // saved program is loaded.
  function loadFiles(files, active) {
    for (const model of fileModels.values()) model.dispose();
    fileModels.clear();

    const entry = typeof files[ENTRY_FILE] === "string" ? files[ENTRY_FILE] : "";
    fileModels.set(ENTRY_FILE, makeModel(ENTRY_FILE, entry));
    for (const [name, source] of Object.entries(files)) {
      if (name !== ENTRY_FILE && FILE_NAME_RE.test(name)) {
        fileModels.set(name, makeModel(name, source));
      }
    }
    for (const model of fileModels.values()) model.onDidChangeContent(persistDraft);

    setActiveFile(fileModels.has(active) ? active : ENTRY_FILE);
    renderFileTabs();
    persistDraft();
  }

  function setActiveFile(name) {
    if (!fileModels.has(name)) return;
    activeFile = name;
    if (monacoEditor) monacoEditor.setModel(fileModels.get(name));
    renderFileTabs();
    persistDraft();
  }

  function addFile(name) {
    if (fileModels.has(name)) return false;
    const model = makeModel(name, `# ${name}\n`);
    model.onDidChangeContent(persistDraft);
    fileModels.set(name, model);
    setActiveFile(name);
    return true;
  }

  function renameFile(oldName, newName) {
    if (oldName === ENTRY_FILE || !fileModels.has(oldName) || fileModels.has(newName)) return false;
    // Models are keyed by URI, so a rename means a new model; rebuild the map in
    // place to keep the tab in its original position.
    const entries = [...fileModels.entries()].map(([name, model]) =>
      name === oldName ? [newName, makeModel(newName, model.getValue())] : [name, model]);
    fileModels.get(oldName).dispose();
    fileModels.clear();
    for (const [name, model] of entries) fileModels.set(name, model);
    fileModels.get(newName).onDidChangeContent(persistDraft);
    setActiveFile(newName);
    return true;
  }

  function deleteFile(name) {
    if (name === ENTRY_FILE || !fileModels.has(name)) return;
    fileModels.get(name).dispose();
    fileModels.delete(name);
    if (activeFile === name) setActiveFile(ENTRY_FILE);
    else renderFileTabs();
    persistDraft();
  }

  function renderFileTabs() {
    const strip = document.getElementById("file-tabs");
    if (!strip) return;
    strip.replaceChildren();

    for (const name of fileModels.keys()) {
      const tab = document.createElement("div");
      tab.className = "sim-file-tab";
      if (name === activeFile) tab.classList.add("is-active");
      if (name === ENTRY_FILE) tab.classList.add("is-entry");

      const open = document.createElement("button");
      open.type = "button";
      open.className = "sim-file-tab-name";
      open.textContent = name;
      open.setAttribute("role", "tab");
      open.setAttribute("aria-selected", String(name === activeFile));
      open.title = name === ENTRY_FILE
        ? "main.py is the entry point"
        : `${name} — double-click to rename`;
      open.addEventListener("click", () => setActiveFile(name));
      if (name !== ENTRY_FILE) {
        open.addEventListener("dblclick", () => openFileNameDialog(name));
      }
      tab.append(open);

      if (name !== ENTRY_FILE) {
        const close = document.createElement("button");
        close.type = "button";
        close.className = "sim-file-tab-close";
        close.textContent = "×";
        close.title = `Delete ${name}`;
        close.setAttribute("aria-label", `Delete ${name}`);
        close.addEventListener("click", (event) => {
          event.stopPropagation();
          deleteFile(name);
        });
        tab.append(close);
      }
      strip.append(tab);
    }
  }

  function persistDraft() {
    if (!fileModels.size) return;
    try {
      localStorage.setItem(DRAFT_STORAGE_KEY,
        JSON.stringify({ files: allFiles(), active: activeFile }));
    } catch (e) {}
    refreshProgramLabel();
  }

  // Key order would otherwise make a rename look like an edit.
  function programSnapshot(files, width, height, shape) {
    const sorted = {};
    for (const name of Object.keys(files).sort()) sorted[name] = files[name];
    return JSON.stringify({ files: sorted, width, height, shape });
  }

  // Compared against the stored project rather than tracked with a flag, so
  // editing something back to its saved state clears the marker honestly.
  function isProgramDirty() {
    const name = currentProjectName();
    if (!name) return true;
    const project = readProjects()[name];
    if (!project) return true;
    const { width, height, shape } = currentResolution;
    return programSnapshot(allFiles(), width, height, shape) !==
      programSnapshot(project.files || {}, project.width, project.height, project.shape);
  }

  function refreshProgramLabel() {
    const label = document.getElementById("program-name");
    const dirty = document.getElementById("program-dirty");
    const button = document.getElementById("program-btn");
    if (!label || !dirty || !button) return;
    const name = currentProjectName();
    label.textContent = name || "Unsaved";
    dirty.hidden = !isProgramDirty();
    button.title = name
      ? `${name} — save this program (Ctrl+S)`
      : "Save this program (Ctrl+S)";
  }

  function readDraft() {
    try {
      const draft = JSON.parse(localStorage.getItem(DRAFT_STORAGE_KEY) || "null");
      if (draft && draft.files && typeof draft.files === "object") return draft;
      // Drafts from before multi-file were a bare string under another key.
      const legacy = localStorage.getItem(LEGACY_CODE_KEY);
      if (legacy) {
        localStorage.removeItem(LEGACY_CODE_KEY);
        return { files: { [ENTRY_FILE]: legacy }, active: ENTRY_FILE };
      }
    } catch (e) {}
    return null;
  }

  // ---- new file / rename dialog -------------------------------------------

  let renameTarget = null;

  function openFileNameDialog(target = null) {
    const dialog = document.getElementById("file-name-dialog");
    const input = document.getElementById("file-name-input");
    if (!dialog || !dialog.showModal) return;
    renameTarget = target;
    document.getElementById("file-name-title").textContent = target ? "Rename file" : "New file";
    document.getElementById("file-name-ok").textContent = target ? "Rename" : "Create";
    setFileNameError("");
    input.value = target || "";
    dialog.showModal();
    input.focus();
    input.select();
  }

  function setFileNameError(message) {
    const el = document.getElementById("file-name-error");
    if (!el) return;
    el.textContent = message;
    el.hidden = !message;
  }

  function initFileNameDialog() {
    const dialog = document.getElementById("file-name-dialog");
    const form = document.getElementById("file-name-form");
    const input = document.getElementById("file-name-input");
    if (!dialog || !form) return;

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      let name = input.value.trim();
      if (name && !name.endsWith(".py")) name += ".py";
      if (!FILE_NAME_RE.test(name)) {
        setFileNameError("Use a Python module name: letters, digits and underscores, ending in .py");
        return;
      }
      if (name !== renameTarget && fileModels.has(name)) {
        setFileNameError(`${name} already exists`);
        return;
      }
      if (renameTarget ? renameFile(renameTarget, name) : addFile(name)) dialog.close();
    });

    input.addEventListener("input", () => setFileNameError(""));
    document.getElementById("file-name-cancel")?.addEventListener("click", () => dialog.close());
    document.getElementById("add-file-btn")?.addEventListener("click", () => openFileNameDialog());
  }

  // =========================================================================
  // Monaco Editor Initialization
  // =========================================================================

  function initMonaco() {
    if (typeof require === "undefined") {
      console.error("Monaco loader not found.");
      return;
    }

    require.config({ paths: { vs: MONACO_BASE + "vs" } });
    require(["vs/editor/editor.main"], function () {
      const isLight = document.documentElement.getAttribute("data-theme") === "light";

      monacoEditor = monaco.editor.create(document.getElementById("editor-container"), {
        language: "python",
        theme: isLight ? "vs" : "vs-dark",
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 4,
        insertSpaces: true,
        wordWrap: "on",
        lineNumbers: "on",
        renderLineHighlight: "all",
        padding: { top: 12, bottom: 12 }
      });
      window.monacoEditor = monacoEditor;

      loadFiles(loadInitialFiles(), readDraft()?.active);

      // Shortcut: Ctrl+Enter / Cmd+Enter to Run
      monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, function () {
        runScript();
      });
    });
  }

  // =========================================================================
  // Direct MicroPython Runtime Mount
  // =========================================================================

  const RESOLUTION_STORAGE_KEY = "pydevices-simulator-resolution";

  const XTERM_BASE = "/vendor/xterm/";

  let directMicroPython = null;
  let term = null;
  let fitAddon = null;

  // Keystrokes must reach replProcessCharWithAsyncify strictly one at a time --
  // the Asyncify runtime rejects a second operation while one is in flight.
  let replQueue = Promise.resolve();
  let replPending = 0;
  let busyTimer = 0;

  const TERMINAL_THEMES = {
    dark: {
      background: "#080c14", foreground: "#cbd5e1",
      cursor: "#f97316", cursorAccent: "#080c14", selectionBackground: "#334155",
      black: "#0f172a", red: "#f87171", green: "#34d399", yellow: "#fbbf24",
      blue: "#60a5fa", magenta: "#c084fc", cyan: "#22d3ee", white: "#e2e8f0",
      brightBlack: "#64748b", brightRed: "#fca5a5", brightGreen: "#6ee7b7",
      brightYellow: "#fcd34d", brightBlue: "#93c5fd", brightMagenta: "#d8b4fe",
      brightCyan: "#67e8f9", brightWhite: "#f8fafc"
    },
    light: {
      background: "#ffffff", foreground: "#1e293b",
      cursor: "#ea580c", cursorAccent: "#ffffff", selectionBackground: "#cbd5e1",
      black: "#1e293b", red: "#dc2626", green: "#059669", yellow: "#b45309",
      blue: "#2563eb", magenta: "#9333ea", cyan: "#0891b2", white: "#475569",
      brightBlack: "#94a3b8", brightRed: "#ef4444", brightGreen: "#10b981",
      brightYellow: "#d97706", brightBlue: "#3b82f6", brightMagenta: "#a855f7",
      brightCyan: "#06b6d4", brightWhite: "#0f172a"
    }
  };

  // Runtime bytes arrive one at a time (linebuffer:false). Batch them per frame
  // so a chatty program does not trigger a terminal reflow per character.
  const outputDecoder = new TextDecoder();
  let pendingText = "";
  let flushScheduled = false;
  let activeStream = "stdout";

  function flushTerminal() {
    flushScheduled = false;
    if (!term || !pendingText) return;
    const text = pendingText;
    pendingText = "";
    term.write(text);
  }

  // Colour a run of stderr bytes red rather than wrapping each byte, since the
  // runtime hands us one byte at a time.
  function emitTerminal(text, stream = "stdout") {
    if (stream !== activeStream) {
      pendingText += stream === "stderr" ? "\x1b[31m" : "\x1b[0m";
      activeStream = stream;
    }
    pendingText += text;
    if (!flushScheduled) {
      flushScheduled = true;
      requestAnimationFrame(flushTerminal);
    }
  }

  // Runtime output funnels through here. While the editor runs, stdout carries
  // raw-REPL framing that the user should not see, so the capture intercepts it.
  function writeTerminal(chunk, stream = "stdout") {
    const text = typeof chunk === "string"
      ? chunk
      : outputDecoder.decode(chunk, { stream: true });
    if (rawCapture && stream === "stdout") {
      captureText(text);
      return;
    }
    emitTerminal(text, stream);
  }

  function isReplBusy() {
    return replPending > 0;
  }

  // Typing a single character also goes through the queue, so only announce
  // "Running" once an operation has outlived a keystroke.
  function markBusy() {
    if (busyTimer) return;
    busyTimer = setTimeout(() => {
      busyTimer = 0;
      if (isReplBusy()) {
        setStatus("Running…", "busy");
        if (elStopBtn) elStopBtn.disabled = false;
      }
    }, 150);
  }

  function markIdle() {
    if (busyTimer) {
      clearTimeout(busyTimer);
      busyTimer = 0;
    }
    if (elStopBtn) elStopBtn.disabled = true;
    setStatus("Ready", "ready");
  }

  function enqueueReplBytes(bytes) {
    if (!directMicroPython) return replQueue;
    replPending += 1;
    markBusy();
    replQueue = replQueue
      .then(async () => {
        for (const byte of bytes) {
          await directMicroPython.replProcessCharWithAsyncify(byte);
        }
      })
      .catch((err) => {
        writeTerminal(`\r\n[repl error] ${err && (err.message || err)}\r\n`);
      })
      .then(() => {
        replPending -= 1;
        if (replPending === 0) markIdle();
      });
    return replQueue;
  }

  async function sendReplText(text) {
    await enqueueReplBytes(new TextEncoder().encode(text));
  }

  async function submitRepl(command) {
    await sendReplText(command + "\r");
  }

  // Runs code without disturbing REPL state or the visible prompt -- used for
  // housekeeping like pushing a new display size in. Still queued, because
  // Asyncify permits only one operation in flight.
  function enqueuePython(code) {
    if (!directMicroPython) return Promise.resolve();
    replPending += 1;
    markBusy();
    replQueue = replQueue
      .then(() => directMicroPython.runPythonAsync(code))
      .catch((err) => {
        writeTerminal(`\r\n[runtime] ${err && (err.message || err)}\r\n`, "stderr");
      })
      .then(() => {
        replPending -= 1;
        if (replPending === 0) markIdle();
      });
    return replQueue;
  }

  // =========================================================================
  // Raw-REPL Execution
  // =========================================================================
  //
  // The friendly REPL echoes every character it is fed, so running the editor
  // through it used to splatter a long exec(compile(...)) line across the
  // terminal before any real output appeared. The raw REPL (Ctrl-A) accepts
  // code silently and frames the result on stdout as:
  //
  //     "OK" <program output> \x04 <traceback> \x04 ">"
  //
  // We stream the program output through and swallow the framing. Both REPLs
  // execute in __main__, so globals still persist from run to run.

  let rawCapture = null;

  function captureText(text) {
    const cap = rawCapture;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      if (cap.state === "await-ok") {
        // Everything up to "OK" is the raw-REPL banner and prompt.
        cap.scan = (cap.scan + ch).slice(-2);
        if (cap.scan === "OK") cap.state = "stdout";
      } else if (cap.state === "stdout") {
        if (ch === "\x04") cap.state = "stderr";
        else if (!cap.silent) emitTerminal(ch, "stdout");
      } else if (cap.state === "stderr") {
        if (ch === "\x04") cap.state = "done";
        else cap.errorText += ch;
      }
      // "done": swallow the trailing ">" and the friendly-REPL banner.
    }
    if (cap.state === "done" && cap.errorText && !cap.errorFlushed) {
      cap.errorFlushed = true;
      if (!cap.silent) emitTerminal(cap.errorText, "stderr");
    }
  }

  // Resolves to the traceback text (empty string when the run succeeded).
  async function execRaw(source, { silent = false } = {}) {
    if (!directMicroPython) return "";
    const cap = { state: "await-ok", scan: "", errorText: "", errorFlushed: false, silent };
    rawCapture = cap;
    try {
      // Ctrl-C first: readline only treats Ctrl-A as "enter raw REPL" when the
      // line is empty, otherwise it means "go to start of line".
      await sendReplText("\x03\x01" + source + "\x04");
      await sendReplText("\x02");
    } finally {
      rawCapture = null;
    }
    if (!silent) emitTerminal("\r\n>>> ", "stdout");
    return cap.errorText;
  }

  // Ctrl-C has to bypass the queue: the queue is blocked awaiting the very
  // command we are trying to stop, so a queued interrupt would never arrive.
  // This lands whenever the VM yields; a loop that never yields (for example
  // time.sleep_ms, which busy-waits) still blocks the browser's main thread.
  function interruptRuntime() {
    if (!window.Module) return false;
    try {
      Module.ccall("mp_sched_keyboard_interrupt", "null", [], []);
      return true;
    } catch (err) {
      return false;
    }
  }

  function requestInterrupt() {
    if (isReplBusy()) {
      if (!interruptRuntime()) showToast("Unable to interrupt the runtime");
    } else {
      enqueueReplBytes(new Uint8Array([3]));
    }
    // Clicking the toolbar button moves focus off the terminal; hand it back so
    // typing continues to reach the REPL.
    if (term) term.focus();
  }

  async function mountTerminal(host) {
    const [{ Terminal }, { FitAddon }] = await Promise.all([
      import(XTERM_BASE + "xterm-DrSYbXEP.js"),
      import(XTERM_BASE + "xterm_addon-fit-DxKdSnof.js")
    ]);

    term = new Terminal({
      // MicroPython's print() emits a bare \n; without this the terminal
      // staircases every line of program output.
      convertEol: true,
      cursorBlink: true,
      fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
      fontSize: 12,
      scrollback: 5000,
      theme: TERMINAL_THEMES[currentTheme()]
    });
    fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    host.replaceChildren();
    term.open(host);
    refitTerminal();

    term.onData((data) => {
      if (data === "\x03" && isReplBusy()) {
        requestInterrupt();
        return;
      }
      enqueueReplBytes(new TextEncoder().encode(data));
    });

    // Keeps the terminal correct through splitter drags, window resizes and
    // the pane collapsing -- cheaper than wiring every one of those by hand.
    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(refitTerminal).observe(host);
    }
    window.__pydevicesTerminal = term;
    return term;
  }

  function refitTerminal() {
    if (!fitAddon || !term) return;
    try {
      fitAddon.fit();
    } catch (err) {
      /* pane hidden or zero-sized; the next resize will settle it */
    }
  }

  async function mountRuntime() {
    const host = document.getElementById("console-log");
    if (!host) return;

    setStatus("Refreshing environment…", "busy");
    try {
      await mountTerminal(host);
      const mipIndex = "https://PyDevices.github.io/mip";
      const { loadMicroPython } = await import("/vendor/micropython/micropython.mjs");
      directMicroPython = await loadMicroPython({
        stdout: (chunk) => writeTerminal(chunk, "stdout"),
        stderr: (chunk) => writeTerminal(chunk, "stderr"),
        heapsize: 16 * 1024 * 1024,
        linebuffer: false
      });
      await directMicroPython.runPythonAsync(`
import os, sys
from displaydev import env_set
env_set("PYDEVICES_WIDTH", ${Number(window.SIM_WIDTH)})
env_set("PYDEVICES_HEIGHT", ${Number(window.SIM_HEIGHT)})
sys.path[:] = [".", ".frozen", "lib", "utils"]
import mip
mip.install("pydevices-desktop", index=${JSON.stringify(mipIndex)}, target="lib")
os.chdir("/")
`);
      directMicroPython.replInit();
      if (term) term.focus();
      window.__pydevicesSimulator = {
        phase: "ready",
        runtime: "micropython",
        mp: directMicroPython,
        term,
        runEditor: runScript,
        sendRepl: submitRepl,
        interrupt: requestInterrupt
      };
      setStatus("Ready", "ready");
    } catch (err) {
      writeTerminal(`\r\n${String(err && (err.stack || err))}\r\n`, "stderr");
      window.__pydevicesSimulator = { phase: "failed", runtime: "micropython", error: String(err) };
      setStatus("Runtime error", "error");
    }
  }

  function clearEditorMarkers() {
    if (typeof monaco === "undefined") return;
    for (const model of fileModels.values()) {
      monaco.editor.setModelMarkers(model, "pydevices", []);
    }
  }

  // The entry file is compiled by the raw REPL as "<stdin>"; imported modules
  // keep their own names. Either way a frame maps onto one of our tabs.
  function markTraceback(text) {
    if (typeof monaco === "undefined" || !monacoEditor || !text) return;

    const frames = [];
    const pattern = /File "([^"]+)", line (\d+)/g;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const raw = match[1];
      // Imports resolve through sys.path, so frames arrive as "./helper.py".
      // Anything still holding a slash came from lib/ and is not ours to mark.
      const name = raw === "<stdin>" ? ENTRY_FILE : raw.replace(/^\.?\/+/, "");
      if (name.includes("/")) continue;
      const model = fileModels.get(name);
      if (!model) continue;
      const line = Math.min(parseInt(match[2], 10), model.getLineCount());
      if (line > 0) frames.push({ name, model, line });
    }
    if (!frames.length) return;

    // The last non-empty line of a traceback is the exception itself.
    const summary = text.trim().split("\n").map((l) => l.trim()).filter(Boolean).pop() || "Error";
    const byFile = new Map();
    for (const frame of frames) {
      if (!byFile.has(frame.name)) byFile.set(frame.name, []);
      byFile.get(frame.name).push(frame);
    }
    for (const group of byFile.values()) {
      monaco.editor.setModelMarkers(group[0].model, "pydevices", group.map((frame) => ({
        severity: monaco.MarkerSeverity.Error,
        message: summary,
        startLineNumber: frame.line,
        endLineNumber: frame.line,
        startColumn: 1,
        endColumn: frame.model.getLineMaxColumn(frame.line)
      })));
    }

    // Surface where it actually blew up, which may be in another tab.
    const innermost = frames[frames.length - 1];
    if (innermost.name !== activeFile) setActiveFile(innermost.name);
    monacoEditor.revealLineInCenterIfOutsideViewport(innermost.line);
  }

  // Names written to the runtime FS, so files deleted in the editor can be
  // removed from it too rather than lingering as importable ghosts.
  let writtenFiles = new Set();

  function syncFilesToRuntime() {
    const files = allFiles();
    for (const [name, source] of Object.entries(files)) {
      directMicroPython.FS.writeFile("/" + name, source);
    }
    for (const stale of writtenFiles) {
      if (!(stale in files)) {
        try {
          directMicroPython.FS.unlink("/" + stale);
        } catch (e) {}
      }
    }
    writtenFiles = new Set(Object.keys(files));
  }

  // Execute the entry file through the raw REPL so it uses the persistent
  // __main__ namespace. Imports and assignments remain available at the next
  // prompt -- which also means an edited module keeps the version the running
  // VM already imported, so Reset VM is the way to pick changes up.
  async function runScript() {
    if (!directMicroPython || isReplBusy()) return;
    persistState();
    clearEditorMarkers();
    syncFilesToRuntime();
    hasRunSinceBoot = true;
    if (elRunBtn) elRunBtn.disabled = true;
    if (term) term.focus();
    try {
      emitTerminal(`\r\n\x1b[38;2;245;78;0m▶ ${ENTRY_FILE}\x1b[0m\r\n`, "stdout");
      markTraceback(await execRaw(entrySource()));
    } finally {
      if (elRunBtn) elRunBtn.disabled = false;
    }
  }

  function resetVm() {
    persistState();
    window.location.reload();
  }

  async function enableAudio(microphone) {
    const button = document.getElementById(microphone ? "enable-microphone" : "enable-audio");
    if (!window.Module || !Module.pydevicesBridge) {
      showToast("Direct MicroPython must be running");
      return;
    }
    button.disabled = true;
    try {
      const permission = await Promise.race([
        Module.pydevicesBridge.enableAudio(microphone),
        new Promise((_, reject) => setTimeout(() => reject(new Error("Permission timed out")), 5000))
      ]);
      if (!permission.audio || (microphone && !permission.microphone)) throw new Error("Permission not granted");
      setButtonLabel(button, microphone ? "Microphone Enabled" : "Audio Enabled");
    } catch (err) {
      button.disabled = false;
      showToast(String(err.message || err));
    }
  }

  function persistState() {
    persistDraft();
    try {
      localStorage.setItem(RESOLUTION_STORAGE_KEY, JSON.stringify(currentResolution));
    } catch (e) {}
  }

  function restoreResolution() {
    try {
      const saved = JSON.parse(localStorage.getItem(RESOLUTION_STORAGE_KEY) || "null");
      if (saved && saved.width > 0 && saved.height > 0) {
        setCanvasResolution(saved.width, saved.height, saved.shape || "rectangle");
        return true;
      }
    } catch (e) {}
    return false;
  }

  // Monaco loads asynchronously, so fall back to the same draft/template
  // resolution the editor itself uses -- otherwise an early caller would get the
  // default template instead of the user's saved code.
  window.getEditorCode = function() {
    if (fileModels.size) return entrySource();
    try {
      return loadInitialFiles()[ENTRY_FILE] || "";
    } catch (e) {
      return "";
    }
  };

  // =========================================================================
  // Canvas Resolution & Device Presets
  // =========================================================================

  function clearCanvas() {
    if (!elCanvas) return;
    const ctx = elCanvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, elCanvas.width, elCanvas.height);
    }
  }

  function setCanvasResolution(width, height, shape = "rectangle") {
    currentResolution = { width, height, shape };
    // Read by the Python bootstrap to pin the panel size; see _set_board_size().
    window.SIM_WIDTH = width;
    window.SIM_HEIGHT = height;
    if (!elCanvas) return;

    elCanvas.width = width;
    elCanvas.height = height;
    clearCanvas();

    if (elDeviceBezel) {
      if (shape === "round") {
        elDeviceBezel.classList.add("is-round");
      } else {
        elDeviceBezel.classList.remove("is-round");
      }
    }
  }

  function syncResolutionSelect() {
    if (!elResolutionSelect) return;
    const { width, height, shape } = currentResolution;
    const suffix = shape === "round" ? "-round" : shape === "square" ? "-square" : "";
    const key = `${width}x${height}${suffix}`;
    if (elResolutionSelect.querySelector(`option[value="${key}"]`)) elResolutionSelect.value = key;
  }

  function setStageNotice(visible) {
    const notice = document.getElementById("stage-notice");
    if (notice) notice.hidden = !visible;
  }

  // The bootstrap reads PYDEVICES_WIDTH/HEIGHT once at import time, so pushing
  // them again lets a program that has not built its display yet pick the new
  // size up without a reload.
  function applyResolutionToVm() {
    if (!directMicroPython) return;
    enqueuePython(
      "from displaydev import env_set\n" +
      `env_set("PYDEVICES_WIDTH", ${Number(currentResolution.width)})\n` +
      `env_set("PYDEVICES_HEIGHT", ${Number(currentResolution.height)})\n`
    );
  }

  function commitResolution(width, height, shape) {
    setCanvasResolution(width, height, shape);
    syncResolutionSelect();
    persistState();
    applyResolutionToVm();
    if (hasRunSinceBoot) setStageNotice(true);
  }

  function openCustomResolution() {
    const dialog = document.getElementById("custom-res-dialog");
    const inputW = document.getElementById("custom-res-w");
    const inputH = document.getElementById("custom-res-h");
    if (!dialog || !dialog.showModal) {
      // No <dialog> support: keep the old path rather than losing the feature.
      const w = parseInt(prompt("Enter display width (px):", currentResolution.width), 10);
      const h = parseInt(prompt("Enter display height (px):", currentResolution.height), 10);
      if (w > 0 && h > 0) commitResolution(w, h, "rectangle");
      else syncResolutionSelect();
      return;
    }
    inputW.value = currentResolution.width;
    inputH.value = currentResolution.height;
    dialog.showModal();
    inputW.focus();
    inputW.select();
  }

  const RESOLUTION_PRESETS = {
    "320x240": [320, 240, "rectangle"],
    "240x320": [240, 320, "rectangle"],
    "240x240-square": [240, 240, "square"],
    "240x240-round": [240, 240, "round"],
    "480x320": [480, 320, "rectangle"],
    "320x480": [320, 480, "rectangle"],
    "800x480": [800, 480, "rectangle"]
  };

  function handleResolutionChange(val) {
    const preset = RESOLUTION_PRESETS[val];
    if (preset) commitResolution(preset[0], preset[1], preset[2]);
    else if (val === "custom") openCustomResolution();
  }

  function initCustomResolutionDialog() {
    const dialog = document.getElementById("custom-res-dialog");
    const form = document.getElementById("custom-res-form");
    if (!dialog || !form) return;

    form.addEventListener("submit", () => {
      const w = parseInt(document.getElementById("custom-res-w").value, 10);
      const h = parseInt(document.getElementById("custom-res-h").value, 10);
      if (w > 0 && h > 0) commitResolution(w, h, "rectangle");
      else syncResolutionSelect();
    });

    document.getElementById("custom-res-cancel")?.addEventListener("click", () => dialog.close());
    // Covers Escape as well as the Cancel button: the select is still showing
    // "Custom...", so put it back on whatever is actually on screen.
    dialog.addEventListener("close", syncResolutionSelect);
  }

  // =========================================================================
  // Templates
  // =========================================================================

  // Templates are still single-file; `files` lets one grow extra modules later
  // without another format change.
  function templateFiles(tpl) {
    return tpl.files ? { ...tpl.files } : { [ENTRY_FILE]: tpl.code };
  }

  function loadInitialFiles() {
    // 1. Check URL hash (#template=...)
    const hash = window.location.hash.substring(1);
    if (hash) {
      const params = new URLSearchParams(hash);
      const templateKey = params.get("template");
      if (templateKey && SIMULATOR_TEMPLATES[templateKey]) {
        if (elTemplateSelect) elTemplateSelect.value = templateKey;
        const tpl = SIMULATOR_TEMPLATES[templateKey];
        setCanvasResolution(tpl.width, tpl.height, tpl.shape);
        return templateFiles(tpl);
      }
    }

    // 2. Check the locally saved draft
    const draft = readDraft();
    if (draft) return draft.files;

    // 3. Default to LVGL counter template
    const def = SIMULATOR_TEMPLATES["lvgl-counter"];
    if (def) {
      setCanvasResolution(def.width, def.height, def.shape);
      return templateFiles(def);
    }
    return { [ENTRY_FILE]: "# PyDevices Simulator\nprint('Hello from PyDevices Simulator!')\n" };
  }

  function loadTemplate(key) {
    if (!SIMULATOR_TEMPLATES[key] || !monacoEditor) return;
    const tpl = SIMULATOR_TEMPLATES[key];
    loadFiles(templateFiles(tpl), ENTRY_FILE);
    clearEditorMarkers();
    commitResolution(tpl.width, tpl.height, tpl.shape);
  }

  // =========================================================================
  // Saved Programs
  // =========================================================================
  //
  // Saves live in this browser's localStorage, keyed by name, and carry the
  // display size the program was written for. The download link is the only way
  // out; there is deliberately no upload counterpart -- pasting into the editor
  // covers the other direction without a file picker.

  const PROJECTS_STORAGE_KEY = "pydevices-simulator-projects";
  const LAST_PROJECT_KEY = "pydevices-simulator-last-project";
  let downloadUrl = "";

  function readProjects() {
    try {
      const parsed = JSON.parse(localStorage.getItem(PROJECTS_STORAGE_KEY) || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function writeProjects(projects) {
    try {
      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects));
      return true;
    } catch (e) {
      // Quota is the realistic failure here, and silently dropping a save is
      // the one outcome worth interrupting the user for.
      showToast("Could not save — browser storage is full");
      return false;
    }
  }

  function currentProjectName() {
    try {
      return localStorage.getItem(LAST_PROJECT_KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function formatSavedAt(iso) {
    const when = new Date(iso);
    if (isNaN(when)) return "";
    return when.toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    });
  }

  function renderProjectList() {
    const list = document.getElementById("save-list");
    const empty = document.getElementById("save-empty");
    if (!list) return;

    const projects = readProjects();
    const names = Object.keys(projects).sort((a, b) =>
      String(projects[b].savedAt || "").localeCompare(String(projects[a].savedAt || "")));
    if (empty) empty.hidden = names.length > 0;

    list.replaceChildren();
    const active = currentProjectName();
    for (const name of names) {
      const entry = projects[name];
      const item = document.createElement("li");
      if (name === active) item.classList.add("is-current");

      const open = document.createElement("button");
      open.type = "button";
      open.className = "sim-save-entry";
      open.title = `Load ${name}`;
      const label = document.createElement("span");
      label.className = "sim-save-entry-name";
      label.textContent = name;
      const meta = document.createElement("span");
      meta.className = "sim-save-entry-meta";
      const count = Object.keys(entry.files || {}).length;
      meta.textContent = [
        formatSavedAt(entry.savedAt),
        `${entry.width}×${entry.height}`,
        count > 1 ? `${count} files` : null
      ].filter(Boolean).join(" · ");
      open.append(label, meta);
      open.addEventListener("click", () => loadProject(name));

      const del = document.createElement("button");
      del.type = "button";
      del.className = "sim-save-delete";
      del.title = `Delete ${name}`;
      del.setAttribute("aria-label", `Delete ${name}`);
      del.textContent = "×";
      del.addEventListener("click", () => deleteProject(name));

      item.append(open, del);
      list.append(item);
    }
  }

  function saveProject(name) {
    const trimmed = name.trim();
    if (!trimmed || !monacoEditor) return false;
    const projects = readProjects();
    projects[trimmed] = {
      files: allFiles(),
      entry: ENTRY_FILE,
      width: currentResolution.width,
      height: currentResolution.height,
      shape: currentResolution.shape,
      savedAt: new Date().toISOString()
    };
    if (!writeProjects(projects)) return false;
    try {
      localStorage.setItem(LAST_PROJECT_KEY, trimmed);
    } catch (e) {}
    renderProjectList();
    refreshProgramLabel();
    showToast(`✓ Saved “${trimmed}”`);
    return true;
  }

  function loadProject(name) {
    const project = readProjects()[name];
    if (!project || !monacoEditor) return;
    loadFiles(project.files || {}, project.entry || ENTRY_FILE);
    clearEditorMarkers();
    if (project.width > 0 && project.height > 0) {
      commitResolution(project.width, project.height, project.shape || "rectangle");
    }
    try {
      localStorage.setItem(LAST_PROJECT_KEY, name);
    } catch (e) {}
    refreshProgramLabel();
    document.getElementById("save-dialog")?.close();
    showToast(`Loaded “${name}”`);
  }

  function deleteProject(name) {
    const projects = readProjects();
    if (!(name in projects)) return;
    delete projects[name];
    writeProjects(projects);
    if (currentProjectName() === name) {
      try {
        localStorage.removeItem(LAST_PROJECT_KEY);
      } catch (e) {}
    }
    renderProjectList();
    refreshProgramLabel();
  }

  // Downloads the file that is currently open, under its own name. One file at a
  // time keeps this a plain link -- bundling a whole program would mean shipping
  // a zip library for it.
  function refreshDownloadLink() {
    const link = document.getElementById("download-py");
    if (!link) return;
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(
      new Blob([fileSource(activeFile)], { type: "text/x-python" }));
    link.href = downloadUrl;
    link.download = activeFile;
    link.textContent = `Download ${activeFile}`;
  }

  function openSaveDialog() {
    const dialog = document.getElementById("save-dialog");
    const nameInput = document.getElementById("save-name");
    if (!dialog || !dialog.showModal) return;
    if (nameInput) nameInput.value = currentProjectName() || "main";
    renderProjectList();
    refreshDownloadLink();
    dialog.showModal();
    if (nameInput) {
      nameInput.focus();
      nameInput.select();
    }
  }

  function initSaveDialog() {
    const dialog = document.getElementById("save-dialog");
    const form = document.getElementById("save-form");
    const nameInput = document.getElementById("save-name");
    if (!dialog || !form) return;

    form.addEventListener("submit", (event) => {
      // method="dialog" would close before the handler could keep it open on a
      // failed save, so drive the close explicitly.
      event.preventDefault();
      if (saveProject(nameInput.value)) dialog.close();
    });

    document.getElementById("save-close")?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => {
      if (downloadUrl) {
        URL.revokeObjectURL(downloadUrl);
        downloadUrl = "";
      }
    });
  }

  // =========================================================================
  // Resizable Split Panes
  // =========================================================================

  // Pointer events rather than mouse events, so a finger on a tablet or an
  // installed PWA drives the same code path. Pointer capture keeps the drag
  // alive when the pointer leaves the 6px splitter or the window entirely.
  function makeDraggable(splitter, cursor, onMove) {
    if (!splitter) return;

    splitter.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 && event.pointerType === "mouse") return;
      event.preventDefault();
      splitter.setPointerCapture(event.pointerId);
      splitter.classList.add("is-dragging");
      document.body.style.cursor = cursor;
      document.body.style.userSelect = "none";
    });

    splitter.addEventListener("pointermove", (event) => {
      if (!splitter.hasPointerCapture(event.pointerId)) return;
      onMove(event);
    });

    const end = (event) => {
      if (!splitter.hasPointerCapture(event.pointerId)) return;
      splitter.releasePointerCapture(event.pointerId);
      splitter.classList.remove("is-dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      if (monacoEditor) monacoEditor.layout();
    };
    splitter.addEventListener("pointerup", end);
    splitter.addEventListener("pointercancel", end);
  }

  function initSplitters() {
    const editorPane = document.getElementById("editor-pane");
    const previewPane = document.getElementById("preview-pane");
    const deviceStage = document.getElementById("device-stage");
    const consolePane = document.getElementById("console-pane");

    if (editorPane && previewPane) {
      makeDraggable(document.getElementById("splitter-v"), "col-resize", (event) => {
        const totalW = window.innerWidth;
        const newLeftW = Math.max(260, Math.min(event.clientX, totalW - 320));
        const pct = (newLeftW / totalW) * 100;
        editorPane.style.flex = `0 0 ${pct}%`;
        previewPane.style.flex = `0 0 ${100 - pct}%`;
        if (monacoEditor) monacoEditor.layout();
      });
    }

    if (previewPane && deviceStage && consolePane) {
      makeDraggable(document.getElementById("splitter-h"), "row-resize", (event) => {
        const bounds = previewPane.getBoundingClientRect();
        const stageH = Math.max(120, Math.min(event.clientY - bounds.top, bounds.height - 120));
        const pct = (stageH / bounds.height) * 100;
        deviceStage.style.flex = `0 0 ${pct}%`;
        consolePane.style.flex = `1 1 ${100 - pct}%`;
      });
    }
  }

  // =========================================================================
  // Overflow Menu
  // =========================================================================

  function initMoreMenu() {
    const button = document.getElementById("more-menu-btn");
    const menu = document.getElementById("more-menu");
    if (!button || !menu) return;

    const close = () => {
      menu.hidden = true;
      button.setAttribute("aria-expanded", "false");
    };

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = menu.hidden;
      menu.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      if (open) menu.querySelector(".sim-menu-item:not(:disabled)")?.focus();
    });

    // Any action inside the menu dismisses it, including the ones that go on to
    // reload the page -- otherwise the menu lingers over the reloading view.
    menu.addEventListener("click", (event) => {
      if (event.target.closest(".sim-menu-item")) close();
    });

    document.addEventListener("click", (event) => {
      if (!menu.hidden && !menu.contains(event.target) && event.target !== button) close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !menu.hidden) {
        close();
        button.focus();
      }
    });
  }

  // =========================================================================
  // Theme Switching (Dark / Light)
  // =========================================================================

  const THEME_STORAGE_KEY = "pydevices-theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function updateThemeUI(theme) {
    const isLight = theme === "light";
    const themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
      themeBtn.innerHTML = isLight
        ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
        : '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
      themeBtn.title = isLight ? "Switch to Dark Theme" : "Switch to Light Theme";
    }
    if (monacoEditor && typeof monaco !== "undefined") {
      monaco.editor.setTheme(isLight ? "vs" : "vs-dark");
    }
    if (term) {
      term.options.theme = TERMINAL_THEMES[isLight ? "light" : "dark"];
    }
  }

  function applyTheme(theme) {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (e) {}
    updateThemeUI(theme);
  }

  function toggleTheme() {
    const next = currentTheme() === "light" ? "dark" : "light";
    applyTheme(next);
  }

  // =========================================================================
  // DOM Event Bindings
  // =========================================================================

  window.addEventListener("DOMContentLoaded", () => {
    initMonaco();
    initSplitters();

    if (elRunBtn) elRunBtn.addEventListener("click", runScript);
    if (elStopBtn) elStopBtn.addEventListener("click", requestInterrupt);
    if (elResetVmBtn) elResetVmBtn.addEventListener("click", resetVm);

    // Ctrl+C inside the terminal is handled by term.onData. This covers the
    // case where focus is elsewhere and a runaway program needs stopping.
    window.addEventListener("keydown", (event) => {
      if (!event.ctrlKey || event.key.toLowerCase() !== "c") return;
      if (!isReplBusy()) return;
      if (window.getSelection && String(window.getSelection())) return;
      event.preventDefault();
      requestInterrupt();
    });
    if (elProgramBtn) elProgramBtn.addEventListener("click", openSaveDialog);
    initSaveDialog();
    initFileNameDialog();
    initMoreMenu();

    // Ctrl+S is the reflex for "save"; without this the browser offers to save
    // the page itself, which is never what is wanted here.
    window.addEventListener("keydown", (event) => {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      openSaveDialog();
    });

    if (elClearConsoleBtn) elClearConsoleBtn.addEventListener("click", clearConsole);
    document.getElementById("refresh-application")?.addEventListener("click", refreshApplication);
    document.getElementById("dismiss-install-hint")?.addEventListener("click", () => {
      const hint = document.getElementById("install-hint");
      if (hint) hint.hidden = true;
      sessionStorage.setItem("sim-install-hint-dismissed", "1");
    });
    window.addEventListener("beforeinstallprompt", showInstallHint);
    window.addEventListener("appinstalled", () => {
      const hint = document.getElementById("install-hint");
      if (hint) hint.hidden = true;
    });
    document.getElementById("enable-audio")?.addEventListener("click", () => enableAudio(false));
    document.getElementById("enable-microphone")?.addEventListener("click", () => enableAudio(true));

    if (elTemplateSelect) {
      elTemplateSelect.addEventListener("change", (e) => loadTemplate(e.target.value));
    }

    if (elResolutionSelect) {
      elResolutionSelect.addEventListener("change", (e) => handleResolutionChange(e.target.value));
    }
    initCustomResolutionDialog();

    document.getElementById("stage-notice-reset")?.addEventListener("click", resetVm);
    document.getElementById("stage-notice-dismiss")?.addEventListener("click", () => setStageNotice(false));

    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      themeToggle.addEventListener("click", toggleTheme);
    }
    updateThemeUI(currentTheme());

    window.addEventListener("resize", () => {
      if (monacoEditor) monacoEditor.layout();
    });

    // Always apply a resolution, so window.SIM_WIDTH/SIM_HEIGHT are set before
    // the bootstrap reads them -- the saved-draft path through loadInitialFiles()
    // returns without touching the canvas.
    if (!restoreResolution()) {
      const { width, height, shape } = currentResolution;
      setCanvasResolution(width, height, shape);
    }
    syncResolutionSelect();
    // Register PWA Service Worker
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("./sw.js", { updateViaCache: "none" }).then((registration) => {
          registration.update();
        }).catch((err) => {
          console.warn("[Simulator] ServiceWorker registration failed:", err);
        });
      });
    }

    // Refresh the environment, then open a REPL before editor code is run.
    mountRuntime();
  });
})();
