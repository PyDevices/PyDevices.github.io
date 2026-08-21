/**
 * simulator.js — Interactive PyDevices Python Simulator Engine
 *
 * Manages Monaco Editor, Pyodide/MicroPython runtime execution,
 * synthetic board_config binding, LZ-string sharing, and split layout.
 */

(function () {
  const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v314.0.5/full/";
  const MONACO_CDN = "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/";
  const INDEX_URLS = [
    "https://test.pypi.org/simple/{package_name}/",
    "https://pypi.org/simple/{package_name}/"
  ];

  let monacoEditor = null;
  let pyodideInstance = null;
  let isRunning = false;
  let currentResolution = { width: 320, height: 240, shape: "rectangle" };

  // DOM Elements
  const elConsole = document.getElementById("console-log");
  const elStatusDot = document.getElementById("status-dot");
  const elStatusText = document.getElementById("status-text");
  const elTemplateSelect = document.getElementById("template-select");
  const elResolutionSelect = document.getElementById("resolution-select");
  const elRuntimeSelect = document.getElementById("runtime-select");
  const elRunBtn = document.getElementById("run-btn");
  const elShareBtn = document.getElementById("share-btn");
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

  function logConsole(text, type = "normal") {
    if (!elConsole) return;
    const span = document.createElement("span");
    if (type === "info") span.className = "log-info";
    else if (type === "success") span.className = "log-success";
    else if (type === "warn") span.className = "log-warn";
    else if (type === "error") span.className = "log-err";
    else if (type === "dim") span.className = "log-dim";

    span.textContent = text;
    elConsole.appendChild(span);
    elConsole.scrollTop = elConsole.scrollHeight;
  }

  function clearConsole() {
    if (elConsole) elConsole.textContent = "";
  }

  function showToast(msg) {
    if (!elToast) return;
    elToast.textContent = msg;
    elToast.classList.add("is-active");
    setTimeout(() => elToast.classList.remove("is-active"), 2600);
  }

  // =========================================================================
  // Monaco Editor Initialization
  // =========================================================================

  function initMonaco() {
    if (typeof require === "undefined") {
      console.error("Monaco loader not found.");
      return;
    }

    require.config({ paths: { vs: MONACO_CDN + "vs" } });
    require(["vs/editor/editor.main"], function () {
      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      const initialCode = loadInitialCode();

      monacoEditor = monaco.editor.create(document.getElementById("editor-container"), {
        value: initialCode,
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

      // Shortcut: Ctrl+Enter / Cmd+Enter to Run
      monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, function () {
        runScript();
      });

      // Auto-save code edits to localStorage
      monacoEditor.onDidChangeModelContent(() => {
        try {
          localStorage.setItem("pydevices-simulator-code", monacoEditor.getValue());
        } catch (e) {}
      });

      logConsole("Monaco editor initialized. Press Ctrl+Enter to run code.\n", "dim");
    });
  }

  // =========================================================================
  // Python Runtime Harness (Pyodide & MicroPython WASM)
  // =========================================================================

  async function getPyodide() {
    if (pyodideInstance) return pyodideInstance;

    setStatus("Booting Python engine…", "busy");
    logConsole("[Runtime] Loading Pyodide WASM environment…\n", "info");

    const { loadPyodide } = await import(PYODIDE_CDN + "pyodide.mjs");
    pyodideInstance = await loadPyodide({
      indexURL: PYODIDE_CDN,
      stdout: (text) => logConsole(text + "\n"),
      stderr: (text) => logConsole(text + "\n", "error")
    });

    setStatus("Loading package tools…", "busy");
    await pyodideInstance.loadPackage("micropip");

    // Setup sys.path and PyScript/DOM shims
    await pyodideInstance.runPythonAsync(`
import sys, os, types
if "/home/pyodide" not in sys.path:
    sys.path.insert(0, "/home/pyodide")
if "." not in sys.path:
    sys.path.insert(0, ".")

# PyScript compatibility shims
if "pyscript" not in sys.modules:
    ps = types.ModuleType("pyscript")
    ps_ffi = types.ModuleType("pyscript.ffi")
    try:
        import pyodide.ffi
        ps_ffi.create_proxy = pyodide.ffi.create_proxy
    except ImportError:
        pass
    from js import document, window
    ps.document = document
    ps.window = window
    ps.ffi = ps_ffi
    sys.modules["pyscript"] = ps
    sys.modules["pyscript.ffi"] = ps_ffi
`);

    // Fetch portable mip.py from vendor chrome
    try {
      const mipRes = await fetch("/vendor/pydevices-chrome/mip.py");
      if (mipRes.ok) {
        const mipCode = await mipRes.text();
        pyodideInstance.FS.writeFile("mip.py", mipCode);
      }
    } catch (e) {
      console.warn("Could not preload local mip.py:", e);
    }

    setStatus("Ready", "ready");
    logConsole("[Runtime] Python environment ready.\n", "success");
    return pyodideInstance;
  }

  async function runScript() {
    if (!monacoEditor) return;
    if (isRunning) {
      logConsole("[Runtime] Execution already in progress…\n", "warn");
      return;
    }

    const code = monacoEditor.getValue();
    if (!code.trim()) {
      logConsole("[Runtime] Editor is empty.\n", "warn");
      return;
    }

    isRunning = true;
    setStatus("Executing script…", "busy");
    logConsole(`\n--- Execution started (${new Date().toLocaleTimeString()}) ---\n`, "dim");

    const t0 = performance.now();

    try {
      const pyodide = await getPyodide();

      // Always install pydevices-desktop for all scenarios
      const depsToInstall = ["pydevices-desktop"];
      if (code.includes("lvgl") || code.includes("lv.") || code.includes("display_driver")) {
        depsToInstall.push("pydevices-lvgl");
      }
      if (code.includes("pdwidgets")) {
        depsToInstall.push("pydevices-pdwidgets");
      }
      if (code.includes("pygraphics") || code.includes("palettes")) {
        depsToInstall.push("pydevices-pygraphics", "pydevices-palettes");
      }

      const micropip = pyodide.pyimport("micropip");
      micropip.set_index_urls(INDEX_URLS);
      for (const dep of Array.from(new Set(depsToInstall))) {
        try {
          await micropip.install(dep);
        } catch (err) {
          console.error(`Package install ${dep} error:`, err);
        }
      }

      // Ensure canvas dimensions match preset
      setCanvasResolution(currentResolution.width, currentResolution.height, currentResolution.shape);

      // Cleanly reset previous driver / event_loop state before user script runs
      await pyodide.runPythonAsync(`
import sys
from displaydev import env_set

env_set("PYDEVICES_WIDTH", ${currentResolution.width})
env_set("PYDEVICES_HEIGHT", ${currentResolution.height})
env_set("PYDEVICES_CANVAS_ID", "display_canvas")

# Clean up active LVGL event loop / display driver if present
if "display_driver" in sys.modules:
    try:
        dd = sys.modules["display_driver"]
        if hasattr(dd, "event_loop"):
            inst = dd.event_loop.current_instance()
            if inst is not None:
                inst.deinit()
        if hasattr(dd, "app"):
            dd.app.stop_timer()
    except Exception:
        pass
    sys.modules.pop("display_driver", None)

# Fully deinit LVGL to prevent orphaned displays and stale render pipelines
try:
    import lvgl as lv
    if lv.is_initialized():
        lv.deinit()
except Exception:
    pass

if "board_config" in sys.modules:
    sys.modules.pop("board_config", None)

if "appdev" in sys.modules:
    try:
        appdev = sys.modules["appdev"]
        if hasattr(appdev.App, "_instance"):
            appdev.App._instance = None
    except Exception:
        pass
`);

      // Execute user script
      await pyodide.runPythonAsync(code);

      // If this is an LVGL script, pump task_handler to ensure immediate paint
      if (code.includes("lvgl") || code.includes("lv.")) {
        await pyodide.runPythonAsync(`
try:
    import lvgl as lv
    if lv.is_initialized():
        lv.task_handler()
        if "display_driver" in sys.modules:
            dd = sys.modules["display_driver"]
            for drv in getattr(dd, "_drivers", []):
                if hasattr(drv, "display_drv") and hasattr(drv.display_drv, "show"):
                    drv.display_drv.show()
except Exception:
    pass
`);
      }

      const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
      logConsole(`--- Completed in ${elapsed}s ---\n`, "success");
      setStatus("Ready", "ready");
    } catch (err) {
      logConsole(`\n[Traceback Error]\n${err}\n`, "error");
      setStatus("Error", "error");
    } finally {
      isRunning = false;
    }
  }

  // =========================================================================
  // Canvas Resolution & Device Presets
  // =========================================================================

  function setCanvasResolution(width, height, shape = "rectangle") {
    currentResolution = { width, height, shape };
    if (!elCanvas) return;

    elCanvas.width = width;
    elCanvas.height = height;

    if (elDeviceBezel) {
      if (shape === "round") {
        elDeviceBezel.classList.add("is-round");
      } else {
        elDeviceBezel.classList.remove("is-round");
      }
    }
  }

  function handleResolutionChange(val) {
    if (val === "320x240") setCanvasResolution(320, 240, "rectangle");
    else if (val === "240x320") setCanvasResolution(240, 320, "rectangle");
    else if (val === "240x240-square") setCanvasResolution(240, 240, "square");
    else if (val === "240x240-round") setCanvasResolution(240, 240, "round");
    else if (val === "480x320") setCanvasResolution(480, 320, "rectangle");
    else if (val === "320x480") setCanvasResolution(320, 480, "rectangle");
    else if (val === "800x480") setCanvasResolution(800, 480, "rectangle");
    else if (val === "custom") {
      const customW = prompt("Enter display width (px):", currentResolution.width);
      const customH = prompt("Enter display height (px):", currentResolution.height);
      const w = parseInt(customW, 10);
      const h = parseInt(customH, 10);
      if (w > 0 && h > 0) setCanvasResolution(w, h, "rectangle");
    }
  }

  // =========================================================================
  // Templates & Code Sharing (LZ-String)
  // =========================================================================

  function loadInitialCode() {
    // 1. Check URL hash (#code=... or #template=...)
    const hash = window.location.hash.substring(1);
    if (hash) {
      const params = new URLSearchParams(hash);
      const compressedCode = params.get("code");
      if (compressedCode && typeof LZString !== "undefined") {
        try {
          const decompressed = LZString.decompressFromEncodedURIComponent(compressedCode);
          if (decompressed) return decompressed;
        } catch (e) {}
      }

      const templateKey = params.get("template");
      if (templateKey && SIMULATOR_TEMPLATES[templateKey]) {
        if (elTemplateSelect) elTemplateSelect.value = templateKey;
        const tpl = SIMULATOR_TEMPLATES[templateKey];
        setCanvasResolution(tpl.width, tpl.height, tpl.shape);
        return tpl.code;
      }
    }

    // 2. Check localStorage saved draft
    try {
      const saved = localStorage.getItem("pydevices-simulator-code");
      if (saved) return saved;
    } catch (e) {}

    // 3. Default to LVGL counter template
    const def = SIMULATOR_TEMPLATES["lvgl-counter"];
    if (def) {
      setCanvasResolution(def.width, def.height, def.shape);
      return def.code;
    }
    return "# PyDevices Simulator\nprint('Hello from PyDevices Simulator!')\n";
  }

  function loadTemplate(key) {
    if (!SIMULATOR_TEMPLATES[key] || !monacoEditor) return;
    const tpl = SIMULATOR_TEMPLATES[key];
    monacoEditor.setValue(tpl.code);
    setCanvasResolution(tpl.width, tpl.height, tpl.shape);

    // Update select dropdowns
    if (elResolutionSelect) {
      const resKey = `${tpl.width}x${tpl.height}` + (tpl.shape === "round" ? "-round" : tpl.shape === "square" ? "-square" : "");
      if (elResolutionSelect.querySelector(`option[value="${resKey}"]`)) {
        elResolutionSelect.value = resKey;
      }
    }

    logConsole(`[Template] Loaded "${tpl.name}". Click Run to execute.\n`, "info");
  }

  function shareCode() {
    if (!monacoEditor || typeof LZString === "undefined") return;
    const code = monacoEditor.getValue();
    const compressed = LZString.compressToEncodedURIComponent(code);
    const shareUrl = `${window.location.origin}${window.location.pathname}#code=${compressed}`;

    navigator.clipboard.writeText(shareUrl).then(() => {
      window.location.hash = `code=${compressed}`;
      showToast("✓ Link copied to clipboard!");
    }).catch(() => {
      prompt("Copy this share URL:", shareUrl);
    });
  }

  // =========================================================================
  // Resizable Split Panes
  // =========================================================================

  function initSplitters() {
    const splitterV = document.getElementById("splitter-v");
    const editorPane = document.getElementById("editor-pane");
    const previewPane = document.getElementById("preview-pane");

    if (splitterV && editorPane && previewPane) {
      let isDragging = false;
      splitterV.addEventListener("mousedown", (e) => {
        isDragging = true;
        splitterV.classList.add("is-dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      });

      window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const totalW = window.innerWidth;
        const newLeftW = Math.max(260, Math.min(e.clientX, totalW - 320));
        const pct = (newLeftW / totalW) * 100;
        editorPane.style.flex = `0 0 ${pct}%`;
        previewPane.style.flex = `0 0 ${100 - pct}%`;
        if (monacoEditor) monacoEditor.layout();
      });

      window.addEventListener("mouseup", () => {
        if (isDragging) {
          isDragging = false;
          splitterV.classList.remove("is-dragging");
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
          if (monacoEditor) monacoEditor.layout();
        }
      });
    }
  }

  // =========================================================================
  // Theme Switching
  // =========================================================================

  function updateEditorTheme() {
    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    if (monacoEditor && typeof monaco !== "undefined") {
      monaco.editor.setTheme(isLight ? "vs" : "vs-dark");
    }
  }

  // =========================================================================
  // DOM Event Bindings
  // =========================================================================

  window.addEventListener("DOMContentLoaded", () => {
    initMonaco();
    initSplitters();

    if (elRunBtn) elRunBtn.addEventListener("click", runScript);
    if (elShareBtn) elShareBtn.addEventListener("click", shareCode);
    if (elClearConsoleBtn) elClearConsoleBtn.addEventListener("click", clearConsole);

    if (elTemplateSelect) {
      elTemplateSelect.addEventListener("change", (e) => loadTemplate(e.target.value));
    }

    if (elResolutionSelect) {
      elResolutionSelect.addEventListener("change", (e) => handleResolutionChange(e.target.value));
    }

    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      themeToggle.addEventListener("click", () => {
        setTimeout(updateEditorTheme, 50);
      });
    }

    window.addEventListener("resize", () => {
      if (monacoEditor) monacoEditor.layout();
    });
  });
})();
