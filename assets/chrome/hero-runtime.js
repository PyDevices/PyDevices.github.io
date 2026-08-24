/** Direct MicroPython host for generated PyDevices hero applications. */
(function () {
  const state = { phase: "idle", heroes: [], errors: [] };
  window.__pydevicesHeroes = state;
  async function launch(container) {
    const canvasId = container.dataset.heroCanvas || "hero_canvas";
    const appName = container.dataset.heroApp || "watch";
    const status = container.querySelector(".hero-canvas-status");
    const setStatus = (text) => { if (status) status.textContent = text; };
    const record = { app: appName, canvas: canvasId, phase: "loading" };
    state.heroes.push(record); state.phase = "loading";
    try {
      setStatus("Booting direct MicroPython…");
      const { loadMicroPython } = await import("/vendor/micropython/micropython.mjs");
      const mp = await loadMicroPython({
        stdout: (line) => console.log(`[${appName}] ${line}`),
        stderr: (line) => console.error(`[${appName}] ${line}`),
        heapsize: 16 * 1024 * 1024
      });
      const response = await fetch(`/assets/apps/${appName}.py`, { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} fetching ${appName}.py`);
      mp.FS.writeFile(`/${appName}.py`, await response.text());
      await mp.runPythonAsync(`
import os, sys
from displaydev import env_set
env_set("PYDEVICES_CANVAS_ID", ${JSON.stringify(canvasId)})
if "/" not in sys.path: sys.path.insert(0, "/")
os.chdir("/")
import mip
mip.install("pydevices-desktop", index="https://PyDevices.github.io/mip", target="lib")
_hero = __import__(${JSON.stringify(appName)})
if hasattr(_hero, "main"): _hero.main(${JSON.stringify(canvasId)})
`);
      record.phase = "ready"; record.mp = mp;
      container.classList.add("active");
      if (status) status.remove();
      state.phase = state.heroes.every((hero) => hero.phase === "ready") ? "ready" : "loading";
      window.dispatchEvent(new CustomEvent("pydevices-heroes-ready", { detail: record }));
    } catch (error) {
      record.phase = "failed"; record.error = String(error && (error.stack || error));
      state.errors.push(record.error); state.phase = "failed";
      setStatus("Live preview offline"); console.error("Direct hero failed:", error);
      fetch("/__debug", { method: "POST", body: JSON.stringify({ level: "error", args: [record.error] }) });
      window.dispatchEvent(new CustomEvent("pydevices-heroes-failed", { detail: record }));
    }
  }
  function start() { document.querySelectorAll("[data-hero-canvas]").forEach(launch); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
