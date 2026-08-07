/* Boo's Game Box — the shell.
 *
 * It boots Pyodide, copies `py/` into the Python filesystem, hands the
 * whole thing to `engine.py`, and then does nothing clever. Every game
 * decision is made in Python; this file only renders Views and posts
 * answers back.
 *
 * Adding a game does not touch this file. The list of games comes from
 * py/games.json, which is also what tells us which .py files to fetch.
 */

/* ── Pinned deliberately. Bump it on purpose, never automatically:
 *    a new Pyodide is a new Python, and a new Python can change a game. ── */
const PYODIDE_VERSION = "314.0.3";
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

/* Where py/ lands inside Pyodide's virtual filesystem. */
const PY_ROOT = "/box";

const MAX_TURNS = 60; // keep the transcript from growing forever on old tablets

const el = (id) => document.getElementById(id);

const ui = {
  loading: el("loading"),
  status: el("loading-status"),
  progress: el("progress"),
  progressFill: el("progress-fill"),
  loadingHelp: el("loading-help"),
  retry: el("retry"),
  picker: el("picker"),
  tiles: el("tiles"),
  iosHint: el("ios-hint"),
  iosHintDismiss: el("ios-hint-dismiss"),
  game: el("game"),
  gameTitle: el("game-title"),
  transcript: el("transcript"),
  prompt: el("prompt"),
  score: el("score"),
  back: el("back"),
  soundToggle: el("sound-toggle"),
};

let engine = null; // PyProxy of engine.py
let catalog = [];
let currentGame = null;
let busy = false;

/* ─────────────────────────────────────────────── boot ── */

function setProgress(percent, words) {
  ui.progressFill.style.width = percent + "%";
  ui.progress.setAttribute("aria-valuenow", String(Math.round(percent)));
  if (words) ui.status.textContent = words;
}

async function fetchText(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Could not read ${path} (${response.status})`);
  return response.text();
}

async function mountPython(pyodide) {
  // games.json is the registry: it decides which .py files exist, which is
  // why adding a game never means editing this file.
  const registryText = await fetchText("py/games.json");
  const ids = (JSON.parse(registryText).games || []);

  const relativePaths = [
    "view.py",
    "engine.py",
    "games/__init__.py",
    ...ids.map((id) => `games/${id.replace(/-/g, "_")}.py`),
  ];

  const sources = await Promise.all(relativePaths.map((rel) => fetchText("py/" + rel)));

  pyodide.FS.mkdirTree(PY_ROOT + "/games");
  const encoder = new TextEncoder();
  pyodide.FS.writeFile(PY_ROOT + "/games.json", encoder.encode(registryText));
  relativePaths.forEach((rel, i) => {
    pyodide.FS.writeFile(PY_ROOT + "/" + rel, encoder.encode(sources[i]));
  });

  pyodide.runPython(
    `import sys\np = ${JSON.stringify(PY_ROOT)}\nif p not in sys.path: sys.path.insert(0, p)`
  );
}

async function boot() {
  ui.retry.hidden = true;
  ui.loadingHelp.hidden = true;
  show("loading");

  try {
    setProgress(8, "Waking up the games…");
    const { loadPyodide } = await import(PYODIDE_URL + "pyodide.mjs");

    setProgress(28, "Unpacking Python…");
    const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

    setProgress(68, "Opening the box…");
    await mountPython(pyodide);

    setProgress(88, "Almost ready…");
    engine = pyodide.pyimport
      ? pyodide.pyimport("engine")
      : pyodide.runPython("import engine\nengine");

    const result = JSON.parse(engine.catalog_json());
    if (!result.ok) throw new Error(result.error || "The game box could not be read.");
    catalog = result.games;

    setProgress(100, "Ready!");
    renderTiles();
    showPicker();
  } catch (error) {
    console.error(error);
    failToBoot();
  }
}

/* A child is reading this on their own. The real error goes to the console
 * for whoever comes to help; the screen gets a sentence. */
function failToBoot() {
  setProgress(100, "The games could not wake up.");
  ui.progressFill.style.background = "var(--coral)";
  ui.loadingHelp.hidden = false;
  ui.loadingHelp.textContent = navigator.onLine
    ? "Something got stuck. Try again in a moment."
    : "There is no internet right now, and the games have not been saved to this device yet.";
  ui.retry.hidden = false;
  ui.retry.focus();
}

/* ───────────────────────────────────────────── screens ── */

function show(name) {
  ui.loading.hidden = name !== "loading";
  ui.picker.hidden = name !== "picker";
  ui.game.hidden = name !== "game";
}

function renderTiles() {
  ui.tiles.replaceChildren();
  for (const game of catalog) {
    const item = document.createElement("li");
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "tile";
    tile.dataset.gameId = game.id;

    const emoji = document.createElement("span");
    emoji.className = "tile-emoji";
    emoji.setAttribute("aria-hidden", "true");
    emoji.textContent = game.emoji;

    const title = document.createElement("h2");
    title.className = "tile-title";
    title.textContent = game.title;

    const blurb = document.createElement("p");
    blurb.className = "tile-blurb";
    blurb.textContent = game.blurb;

    const age = document.createElement("span");
    age.className = "tile-age";
    age.textContent = `Ages ${game.min_age}+`;

    tile.append(emoji, title, blurb, age);
    tile.addEventListener("click", () => openGame(game.id));
    item.appendChild(tile);
    ui.tiles.appendChild(item);
  }
}

function showPicker() {
  currentGame = null;
  show("picker");
  document.title = "Boo's Game Box";
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);
}

function openGame(gameId) {
  const game = catalog.find((g) => g.id === gameId);
  if (!game || busy) return;
  currentGame = game;

  // Emoji in its own span so a narrow phone can drop it and keep the name.
  const titleEmoji = document.createElement("span");
  titleEmoji.className = "game-title-emoji";
  titleEmoji.setAttribute("aria-hidden", "true");
  titleEmoji.textContent = game.emoji + " ";
  ui.gameTitle.replaceChildren(titleEmoji, document.createTextNode(game.title));
  document.title = `${game.title} — Boo's Game Box`;
  ui.transcript.replaceChildren();
  ui.prompt.replaceChildren();
  setScore(null);
  show("game");

  // So the device's back gesture returns to the box instead of leaving.
  history.pushState({ gameId }, "", "#" + gameId);

  // No seed argument: JS `null` does not cross into Python as `None`.
  runBridge(() => engine.start_json(gameId));
}

/* ────────────────────────────────────────── the bridge ── */

function runBridge(call) {
  if (busy) return;
  busy = true;
  setControlsEnabled(false);
  try {
    renderView(JSON.parse(call()));
  } catch (error) {
    console.error(error);
    renderView({
      ok: false,
      lines: ["Oh no — that game got its wires crossed.", "Let's go back to the box."],
      prompt: { kind: "end", label: "", choices: [], min: null, max: null },
      art: "🧩",
      sound: null,
      score: null,
    });
  } finally {
    busy = false;
  }
}

function send(value) {
  runBridge(() => engine.send_json(String(value)));
}

function playAgain() {
  ui.transcript.replaceChildren();
  runBridge(() => engine.restart_json());
}

/* ─────────────────────────────────────────── rendering ── */

function renderView(view) {
  appendTurn(view);
  setScore(view.score);
  playSound(view.sound);
  renderPrompt(view.prompt || { kind: "end" }, view.ok !== false);
  // Only now, because the prompt has just changed how tall the transcript is.
  scrollToNewest();
}

function scrollToNewest() {
  ui.transcript.scrollTop = ui.transcript.scrollHeight;
  requestAnimationFrame(() => {
    ui.transcript.scrollTop = ui.transcript.scrollHeight;
  });
}

function appendTurn(view) {
  const lines = Array.isArray(view.lines) ? view.lines : [];
  if (!lines.length && !view.art) return;

  const turn = document.createElement("div");
  turn.className = view.ok === false ? "turn turn-error" : "turn";

  // Trim blank lines at the edges — they were terminal spacing, and here
  // the gap between turns already does that job.
  let start = 0;
  let end = lines.length;
  while (start < end && lines[start].trim() === "") start++;
  while (end > start && lines[end - 1].trim() === "") end--;

  for (let i = start; i < end; i++) {
    const line = lines[i];
    const p = document.createElement("p");
    p.className = line.trim() === "" ? "line is-blank" : "line";
    p.textContent = line;
    turn.appendChild(p);
  }

  if (view.art) turn.appendChild(renderArt(String(view.art)));

  ui.transcript.appendChild(turn);
  while (ui.transcript.children.length > MAX_TURNS) {
    ui.transcript.removeChild(ui.transcript.firstChild);
  }
}

/* A terminal gives every emoji exactly two columns, and the games pad their
 * art to match — " 5  " for an empty plot, " 🌼 " for a planted one, both
 * four columns wide. A browser does not: emoji come from a separate font
 * whose advance width has nothing to do with the monospace grid, so the
 * pipes drift apart. Wrapping each emoji in a box exactly 2ch wide puts the
 * grid back. This is deliberately game-agnostic — it fixes the garden, the
 * Magic Zoo banner, and any art a future game draws. */
const WIDE_EMOJI = (() => {
  const one = "(?:\\p{Emoji_Presentation}|\\p{Extended_Pictographic}\\uFE0F)";
  try {
    return new RegExp(
      `${one}(?:[\\u{1F3FB}-\\u{1F3FF}]|\\uFE0F|\\u200D${one})*`,
      "gu"
    );
  } catch {
    return null; // no Unicode property escapes; art just renders as-is
  }
})();

function renderArt(text) {
  const pre = document.createElement("pre");
  pre.className = "art";

  if (!WIDE_EMOJI) {
    pre.textContent = text;
    return pre;
  }

  let cut = 0;
  for (const match of text.matchAll(WIDE_EMOJI)) {
    if (match.index > cut) {
      pre.appendChild(document.createTextNode(text.slice(cut, match.index)));
    }
    const cell = document.createElement("span");
    cell.className = "art-emoji";
    cell.textContent = match[0];
    pre.appendChild(cell);
    cut = match.index + match[0].length;
  }
  if (cut < text.length) pre.appendChild(document.createTextNode(text.slice(cut)));
  return pre;
}

function setScore(score) {
  if (typeof score === "number") {
    ui.score.textContent = String(score);
    ui.score.setAttribute("aria-label", `Score: ${score}`);
    ui.score.hidden = false;
  } else {
    ui.score.hidden = true;
  }
}

function renderPrompt(prompt, ok) {
  ui.prompt.replaceChildren();

  const inner = document.createElement("div");
  inner.className = "prompt-inner";

  const kind = ok ? prompt.kind : "end";
  const label = prompt.label || "";

  if (label && kind !== "continue") {
    const p = document.createElement("p");
    p.className = "prompt-label";
    p.textContent = label;
    inner.appendChild(p);
  }

  if (kind === "choice") {
    inner.appendChild(buildChoices(prompt.choices || []));
  } else if (kind === "number" || kind === "text") {
    inner.appendChild(buildEntry(kind, prompt));
  } else if (kind === "continue") {
    inner.appendChild(buildButton(label || "Next", "btn btn-primary", () => send("")));
  } else {
    inner.appendChild(buildEnd(ok));
  }

  ui.prompt.appendChild(inner);

  // Point the child (and the keyboard, and the screen reader) at the answer.
  const first = ui.prompt.querySelector("input, button");
  if (first && (kind === "number" || kind === "text")) {
    first.focus();
  } else {
    ui.prompt.focus({ preventScroll: true });
  }
}

function buildChoices(choices) {
  const wrap = document.createElement("div");
  wrap.className = choices.length <= 2 ? "choices is-few" : "choices";
  for (const choice of choices) {
    wrap.appendChild(
      buildButton(choice.label, "btn", () => send(choice.value))
    );
  }
  return wrap;
}

function buildEntry(kind, prompt) {
  const row = document.createElement("div");
  row.className = "answer-row";

  const input = document.createElement("input");
  input.className = "answer-input";
  input.type = "text";
  input.autocomplete = "off";
  input.enterKeyHint = "go";
  input.setAttribute("aria-label", prompt.label || "Your answer");

  if (kind === "number") {
    input.inputMode = "numeric";
    input.pattern = "[0-9]*";
    input.placeholder = numberPlaceholder(prompt);
  } else {
    input.autocapitalize = "none";
    input.autocorrect = "off";
    input.spellcheck = false;
    input.placeholder = "Type here";
  }

  const go = buildButton("Go", "btn btn-primary", () => {
    const value = input.value;
    input.value = "";
    send(value);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      go.click();
    }
  });

  row.append(input, go);
  return row;
}

function numberPlaceholder(prompt) {
  const lo = prompt.min;
  const hi = prompt.max;
  return typeof lo === "number" && typeof hi === "number" ? `${lo}–${hi}` : "";
}

function buildEnd(ok) {
  const row = document.createElement("div");
  row.className = "end-row";
  if (ok) {
    row.appendChild(buildButton("Play again", "btn btn-reward", playAgain));
  }
  row.appendChild(buildButton("Back to the box", "btn", leaveGame));
  return row;
}

function buildButton(text, className, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function setControlsEnabled(enabled) {
  for (const control of ui.prompt.querySelectorAll("button, input")) {
    control.disabled = !enabled;
  }
}

function leaveGame() {
  if (location.hash) history.back();
  else showPicker();
}

/* ─────────────────────────────────────────────── sound ── */
/* Three short blips made with an oscillator. No files to download, so it
 * works offline, and a parent can switch it off for good. */

const SOUND_KEY = "boo-sound";
const TUNES = {
  correct: [[660, 0.09], [880, 0.12]],
  wrong: [[300, 0.12], [220, 0.16]],
  win: [[523, 0.1], [659, 0.1], [784, 0.1], [1046, 0.22]],
};

let audio = null;
let soundOn = localStorage.getItem(SOUND_KEY) !== "off";

function playSound(name) {
  if (!soundOn || !TUNES[name]) return;
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    if (audio.state === "suspended") audio.resume();
    let at = audio.currentTime;
    for (const [frequency, seconds] of TUNES[name]) {
      const oscillator = audio.createOscillator();
      const gain = audio.createGain();
      oscillator.type = "triangle";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, at);
      gain.gain.exponentialRampToValueAtTime(0.18, at + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, at + seconds);
      oscillator.connect(gain).connect(audio.destination);
      oscillator.start(at);
      oscillator.stop(at + seconds + 0.02);
      at += seconds;
    }
  } catch (error) {
    console.warn("No sound available:", error);
  }
}

function updateSoundButton() {
  ui.soundToggle.textContent = soundOn ? "🔊" : "🔇";
  ui.soundToggle.setAttribute("aria-pressed", String(soundOn));
  ui.soundToggle.setAttribute("aria-label", soundOn ? "Sound on" : "Sound off");
}

/* ──────────────────────────────────────── install hint ── */

const IOS_HINT_KEY = "boo-ios-hint";

function maybeShowIosHint() {
  const ua = navigator.userAgent;
  const isIos =
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    navigator.standalone === true;

  if (isIos && !isStandalone && localStorage.getItem(IOS_HINT_KEY) !== "dismissed") {
    ui.iosHint.hidden = false;
  }
}

/* ───────────────────────────────────────────── wiring ── */

ui.back.addEventListener("click", leaveGame);
ui.retry.addEventListener("click", boot);

ui.soundToggle.addEventListener("click", () => {
  soundOn = !soundOn;
  localStorage.setItem(SOUND_KEY, soundOn ? "on" : "off");
  updateSoundButton();
  if (soundOn) playSound("correct");
});

ui.iosHintDismiss.addEventListener("click", () => {
  ui.iosHint.hidden = true;
  localStorage.setItem(IOS_HINT_KEY, "dismissed");
});

window.addEventListener("popstate", () => {
  if (currentGame) showPicker();
});

updateSoundButton();
maybeShowIosHint();
boot();
