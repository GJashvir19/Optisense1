// Finds the backend by itself: same address when served by the backend, local address when opened by double-click.
const API = location.protocol.startsWith("http") ? location.origin : "http://127.0.0.1:8000";

(function () {
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem("os-theme"); } catch (e) {}
  root.dataset.theme = saved || (matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light");

  const page = location.pathname.split("/").pop() || "index.html";
  const link = (f, t) => `<a href="${f}" class="${page === f ? "on" : ""}">${t}</a>`;
  const nav = document.getElementById("nav");
  if (nav) nav.innerHTML = `<nav><div class="wrap">
    <a class="brand" href="index.html"><span class="dot"></span>OptiSense</a>
    <div class="links">${link("index.html", "Home")}${link("risk.html", "Risk")}${link("warning.html", "Warning")}${link("damage.html", "Damage")}</div>
    <span class="pill" id="api">Checking API…</span>
    <button class="tg" id="tg" aria-label="Switch light or dark theme"></button>
  </div></nav>`;
  const foot = document.getElementById("foot");
  if (foot) foot.innerHTML = `<footer><div class="wrap"><span>OptiSense · Disaster prediction and response</span><span>Keep the backend running to use every page.</span></div></footer>`;

  const tg = document.getElementById("tg");
  function setTheme(t) {
    root.dataset.theme = t;
    if (tg) tg.textContent = t === "dark" ? "☀" : "☾";
    try { localStorage.setItem("os-theme", t); } catch (e) {}
  }
  setTheme(root.dataset.theme);
  if (tg) tg.onclick = () => setTheme(root.dataset.theme === "dark" ? "light" : "dark");

  const pill = document.getElementById("api");
  if (pill) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 3000);
    fetch(API + "/health", { signal: ctl.signal })
      .then(r => r.ok ? Promise.resolve() : Promise.reject())
      .then(() => { pill.textContent = "API connected"; pill.className = "pill ok"; })
      .catch(() => { pill.textContent = "API offline"; pill.className = "pill bad"; })
      .finally(() => clearTimeout(timer));
  }
})();

// Sends data to the backend and returns the JSON answer.
async function post(path, body, isForm) {
  let r;
  try {
    r = await fetch(API + path, {
      method: "POST",
      headers: isForm ? {} : { "Content-Type": "application/json" },
      body: isForm ? body : JSON.stringify(body)
    });
  } catch (e) {
    throw new Error("Can't reach the backend. Start it in the backend folder with: uvicorn main:app --reload");
  }
  if (!r.ok) throw new Error("The backend rejected the request (error " + r.status + "). Check the values and try again.");
  return r.json();
}

function showErr(el, msg) { el.textContent = msg; el.style.display = msg ? "block" : "none"; }