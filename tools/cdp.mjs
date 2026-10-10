/* A minimal Chrome DevTools Protocol client. T082/T083.
 *
 * NOTHING WAS INSTALLED FOR THIS. Node 22 ships a global `WebSocket` and a
 * global `fetch`, and Chrome's debugging endpoint needs only those two, so the
 * browser proof runs with no `package.json`, no `node_modules/`, no Puppeteer
 * and no Playwright. That is not minimalism for its own sake: Constitution
 * Principle II caps upkeep at about 2 hours a week, and a browser-driver
 * dependency tree is the kind of thing that breaks on its own schedule and
 * then has to be fixed before the project's own tests can run at all.
 *
 * Scope: launch, attach to one page, send commands, listen for events, close.
 * It is not a general-purpose driver and does not try to be.
 */

import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

/** Where Chrome is, on this machine's platform. */
export const CHROME_CANDIDATES = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
];

export async function findChrome() {
  const { access } = await import("node:fs/promises");
  const fromEnv = process.env.SANSAD_CHROME;
  const candidates = fromEnv ? [fromEnv, ...CHROME_CANDIDATES] : CHROME_CANDIDATES;
  for (const path of candidates) {
    try {
      await access(path);
      return path;
    } catch {
      /* next */
    }
  }
  throw new Error(
    "no Chrome found. Tried:\n  " +
      candidates.join("\n  ") +
      "\nSet SANSAD_CHROME to the binary.",
  );
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Launch headless Chrome with the upstream BLOCKED AT THE NETWORK LEVEL.
 *
 * `--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1` makes every
 * hostname except the loopback static host unresolvable inside this browser.
 * That is stronger than blocking `sansad.in` by name and it is the point:
 * scenario 12 requires the page to work "with the upstream unreachable", and a
 * named block would still let a request to some other host succeed and go
 * unnoticed. Here nothing but the static host can be reached at all, so a page
 * that needed any outside host would fail visibly rather than quietly work on
 * the test machine.
 */
export async function launchChrome({ allowHosts = ["127.0.0.1"], extraArgs = [] } = {}) {
  const binary = await findChrome();
  const userDataDir = await mkdtemp(join(tmpdir(), "sansad-chrome-"));
  const resolverRules = ["MAP * ~NOTFOUND", ...allowHosts.map((h) => `EXCLUDE ${h}`)].join(" , ");

  const args = [
    "--headless=new",
    "--remote-debugging-port=0",
    `--user-data-dir=${userDataDir}`,
    `--host-resolver-rules=${resolverRules}`,
    // Quiet Chrome's own background traffic, so the network log is the page's
    // requests and not the browser's housekeeping. None of these change how
    // the page itself behaves.
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-domain-reliability",
    "--disable-client-side-phishing-detection",
    "--metrics-recording-only",
    "--no-pings",
    "--safebrowsing-disable-auto-update",
    "--disable-features=OptimizationHints,Translate,MediaRouter,InterestFeedContentSuggestions",
    "--hide-scrollbars",
    "--window-size=1280,900",
    ...extraArgs,
    "about:blank",
  ];

  const child = spawn(binary, args, { stdio: ["ignore", "pipe", "pipe"] });
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += String(chunk);
  });

  const portFile = join(userDataDir, "DevToolsActivePort");
  let port = null;
  for (let attempt = 0; attempt < 100 && port === null; attempt += 1) {
    await sleep(100);
    try {
      const text = await readFile(portFile, "utf8");
      const [first] = text.split("\n");
      if (first && first.trim()) port = Number(first.trim());
    } catch {
      /* not written yet */
    }
  }
  if (port === null) {
    child.kill("SIGKILL");
    await rm(userDataDir, { recursive: true, force: true });
    throw new Error(`Chrome never wrote ${portFile}. stderr:\n${stderr}`);
  }

  return {
    port,
    resolverRules,
    binary,
    async close() {
      child.kill("SIGTERM");
      await sleep(300);
      child.kill("SIGKILL");
      await rm(userDataDir, { recursive: true, force: true });
    },
  };
}

/** One CDP connection, with flat sessions. */
export class CdpSession {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.sessionId = null;

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id !== undefined) {
        const slot = this.pending.get(message.id);
        if (!slot) return;
        this.pending.delete(message.id);
        if (message.error) slot.reject(new Error(`${message.error.message} (${message.method})`));
        else slot.resolve(message.result);
        return;
      }
      for (const callback of this.listeners.get(message.method) ?? []) {
        callback(message.params ?? {}, message.sessionId ?? null);
      }
    });
  }

  on(method, callback) {
    if (!this.listeners.has(method)) this.listeners.set(method, []);
    this.listeners.get(method).push(callback);
  }

  send(method, params = {}, sessionId = this.sessionId) {
    const id = this.nextId++;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, method });
      this.socket.send(JSON.stringify(payload));
    });
  }

  close() {
    this.socket.close();
  }
}

/** Connect to the browser endpoint and attach to a fresh page target. */
export async function attachNewPage(port) {
  const version = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
  const socket = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  const cdp = new CdpSession(socket);
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" }, null);
  const { sessionId } = await cdp.send(
    "Target.attachToTarget",
    { targetId, flatten: true },
    null,
  );
  cdp.sessionId = sessionId;
  return { cdp, targetId, chromeVersion: version.Browser, protocol: version["Protocol-Version"] };
}

/** Poll an expression in the page until it is truthy, or time out. */
export async function waitFor(cdp, expression, { timeoutMs = 20000, everyMs = 100, label } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    const { result } = await cdp.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    last = result.value;
    if (last) return last;
    await sleep(everyMs);
  }
  throw new Error(
    `timed out after ${timeoutMs} ms waiting for ${label ?? expression}; last value ${JSON.stringify(last)}`,
  );
}

/** Evaluate an expression and return its value. */
export async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (exceptionDetails) {
    throw new Error(
      `page threw: ${exceptionDetails.text} ${exceptionDetails.exception?.description ?? ""}`,
    );
  }
  return result.value;
}

export { sleep };
