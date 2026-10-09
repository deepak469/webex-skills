#!/usr/bin/env node

import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { spawn } from "node:child_process";
import { mkdir, readFile, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { homedir, platform, userInfo } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const SERVICE_URL =
  "https://webex-developer-ai-assistant-intb.ciscospark.com";
const API_PREFIX = "/webex-developer-ai-assistant/api/v1";
const TOKEN_SKEW_MS = 60_000;
const REQUEST_TIMEOUT_MS = 20_000;

// Public client: PKCE secures the flow, so there is no client secret.
export const OAUTH_CLIENT_ID =
  "C876332f0f6d5a0a384b9d015ae2696dbfc18cad4a9d1696557d8291a365e94fa";
export const OAUTH_SCOPES = "identity:people_read spark:mcp";
export const CALLBACK_PORT = 17177;
export const REDIRECT_URI = `http://localhost:${CALLBACK_PORT}/callback`;
const DEFAULT_IDBROKER_URL = "https://idbrokerbts.webex.com";
const AUTHORIZE_URL = `${DEFAULT_IDBROKER_URL}/idb/oauth2/v1/authorize`;
const LOGIN_TIMEOUT_MS = 300_000;
const CLUSTER_IDBROKER = new Map([
  ["PF84", "https://idbroker.webex.com"],
  ["PA71", "https://idbroker-ae.webex.com"],
  ["PA61", "https://idbroker-au.webex.com"],
  ["PC75", "https://idbroker-ca.webex.com"],
  ["PS65", "https://idbroker-sg.webex.com"],
  ["P0A1", "https://idbroker-b-us.webex.com"],
  ["PI91", "https://idbroker-in.webex.com"],
  ["PE93", "https://idbroker-eu.webex.com"],
  ["PU39", "https://idbroker-oh.webex.com"],
  ["A52D", "https://idbrokerbts.webex.com"],
]);

class SafeError extends Error {
  constructor(message, { status = null, code = null } = {}) {
    super(message);
    this.name = "SafeError";
    this.status = status;
    this.code = code;
  }
}

export function resolveServiceUrl() {
  let parsed;
  try {
    parsed = new URL(SERVICE_URL);
  } catch {
    throw new SafeError("Knowledge service URL must be an absolute URL");
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new SafeError(
      "Knowledge service URL must not contain credentials, query, or fragment",
    );
  }
  const loopbackHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
  if (
    parsed.protocol !== "https:"
    && !(parsed.protocol === "http:" && loopbackHosts.has(parsed.hostname))
  ) {
    throw new SafeError(
      "Knowledge service URL must use HTTPS unless it targets loopback",
    );
  }
  parsed.pathname = parsed.pathname.replace(/\/+$/, "");
  return parsed.toString().replace(/\/$/, "");
}

export function classifyRequestFailure(
  url,
  error,
  env = process.env,
) {
  const host = new URL(url).host;
  if (
    env.CODEX_SANDBOX_NETWORK_DISABLED === "1"
    && error?.name !== "TimeoutError"
  ) {
    return new SafeError(
      `Codex network permission is required to connect to ${host}. `
        + "Use the shell execution tool's sandbox/network escalation to request "
        + "approval, then rerun this exact helper command once.",
      { code: "network_permission_required" },
    );
  }
  const reason = error?.name === "TimeoutError"
    ? "timed out"
    : "could not be reached";
  return new SafeError(`Webex service ${host} ${reason}`, {
    code: "service_unavailable",
  });
}

function safeResponseMessage(payload, status) {
  if (payload && typeof payload === "object") {
    if (typeof payload.detail === "string") return payload.detail;
    if (typeof payload.error === "string") return payload.error;
    if (typeof payload.message === "string") return payload.message;
    if (Array.isArray(payload.Errors)) {
      const descriptions = payload.Errors
        .map((entry) => (
          entry && typeof entry.description === "string" ? entry.description : null
        ))
        .filter(Boolean);
      if (descriptions.length) return descriptions.join("; ");
    }
  }
  return `Knowledge service returned HTTP ${status}`;
}

async function requestJson(
  serviceUrl,
  path,
  {
    method = "GET",
    headers = {},
    body,
    timeoutMs = REQUEST_TIMEOUT_MS,
  } = {},
) {
  let response;
  try {
    response = await fetch(`${serviceUrl}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      redirect: "error",
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    throw classifyRequestFailure(serviceUrl, error);
  }

  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      throw new SafeError(
        `Knowledge service returned invalid JSON (HTTP ${response.status})`,
        { status: response.status, code: "invalid_response" },
      );
    }
  }
  if (!response.ok) {
    throw new SafeError(safeResponseMessage(payload, response.status), {
      status: response.status,
      code: "http_error",
    });
  }
  return { payload, status: response.status, headers: response.headers };
}

function runProcess(
  command,
  args,
  { input = null, allowFailure = false, env = process.env } = {},
) {
  return new Promise((resolvePromise, rejectPromise) => {
    const child = spawn(command, args, {
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      env,
    });
    const stdout = [];
    const stderr = [];
    let outputBytes = 0;
    let settled = false;
    const rejectOnce = (error) => {
      if (!settled) {
        settled = true;
        rejectPromise(error);
      }
    };
    const collect = (target) => (chunk) => {
      outputBytes += chunk.length;
      if (outputBytes > 1_000_000) {
        child.kill();
        rejectOnce(new SafeError("Secure storage command produced excessive output"));
        return;
      }
      target.push(chunk);
    };
    child.stdout.on("data", collect(stdout));
    child.stderr.on("data", collect(stderr));
    child.on("error", () => {
      rejectOnce(new SafeError("Required operating-system command is unavailable"));
    });
    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      const result = {
        code,
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
      };
      if (code !== 0 && !allowFailure) {
        rejectPromise(new SafeError("Operating-system credential operation failed"));
      } else {
        resolvePromise(result);
      }
    });
    child.stdin.end(input === null ? undefined : input);
  });
}

function storeIdentity(serviceUrl) {
  const digest = createHash("sha256")
    .update(serviceUrl)
    .digest("hex")
    .slice(0, 24);
  return {
    account: userInfo().username,
    service: `com.cisco.webex-developer-knowledge.${digest}`,
    digest,
  };
}

function windowsStorePath(serviceUrl) {
  const { digest } = storeIdentity(serviceUrl);
  const base = process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local");
  return join(base, "Cisco", "WebexDeveloperKnowledge", `${digest}.bin`);
}

export function macOSKeychainSaveArgs(identity, secret) {
  return [
    "add-generic-password",
    "-U",
    "-a",
    identity.account,
    "-s",
    identity.service,
    "-w",
    secret,
  ];
}

async function saveSecret(serviceUrl, secret) {
  if (platform() === "darwin") {
    const identity = storeIdentity(serviceUrl);
    await runProcess(
      "/usr/bin/security",
      macOSKeychainSaveArgs(identity, secret),
    );
    return;
  }
  if (platform() === "win32") {
    const path = windowsStorePath(serviceUrl);
    await mkdir(dirname(path), { recursive: true });
    const script = [
      "$plain=[Console]::In.ReadToEnd()",
      "$bytes=[Text.Encoding]::UTF8.GetBytes($plain)",
      "$encrypted=[Security.Cryptography.ProtectedData]::Protect($bytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)",
      "[IO.File]::WriteAllBytes($env:WEBEX_KNOWLEDGE_STORE_PATH,$encrypted)",
    ].join(";");
    await runProcess(
      "powershell.exe",
      ["-NoProfile", "-NonInteractive", "-Command", script],
      {
        input: secret,
        env: { ...process.env, WEBEX_KNOWLEDGE_STORE_PATH: path },
      },
    );
    return;
  }
  throw new SafeError(
    "Secure token storage is currently supported on macOS and Windows only",
  );
}

async function readSecret(serviceUrl) {
  if (platform() === "darwin") {
    const identity = storeIdentity(serviceUrl);
    const result = await runProcess(
      "/usr/bin/security",
      [
        "find-generic-password",
        "-a",
        identity.account,
        "-s",
        identity.service,
        "-w",
      ],
      { allowFailure: true },
    );
    return result.code === 0 ? result.stdout.trimEnd() : null;
  }
  if (platform() === "win32") {
    const path = windowsStorePath(serviceUrl);
    try {
      await readFile(path);
    } catch (error) {
      if (error && error.code === "ENOENT") return null;
      throw new SafeError("Secure token storage could not be read");
    }
    const script = [
      "$encrypted=[IO.File]::ReadAllBytes($env:WEBEX_KNOWLEDGE_STORE_PATH)",
      "$bytes=[Security.Cryptography.ProtectedData]::Unprotect($encrypted,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)",
      "[Console]::Out.Write([Text.Encoding]::UTF8.GetString($bytes))",
    ].join(";");
    const result = await runProcess(
      "powershell.exe",
      ["-NoProfile", "-NonInteractive", "-Command", script],
      { env: { ...process.env, WEBEX_KNOWLEDGE_STORE_PATH: path } },
    );
    return result.stdout;
  }
  throw new SafeError(
    "Secure token storage is currently supported on macOS and Windows only",
  );
}

async function deleteSecret(serviceUrl) {
  if (platform() === "darwin") {
    const identity = storeIdentity(serviceUrl);
    await runProcess(
      "/usr/bin/security",
      [
        "delete-generic-password",
        "-a",
        identity.account,
        "-s",
        identity.service,
      ],
      { allowFailure: true },
    );
    return;
  }
  if (platform() === "win32") {
    await rm(windowsStorePath(serviceUrl), { force: true });
    return;
  }
  throw new SafeError(
    "Secure token storage is currently supported on macOS and Windows only",
  );
}

function validateTokenRecord(value, serviceUrl) {
  if (
    !value
    || typeof value !== "object"
    || value.service_url !== serviceUrl
    || value.client_id !== OAUTH_CLIENT_ID
  ) {
    return null;
  }
  if (
    typeof value.access_token !== "string"
    || typeof value.refresh_token !== "string"
    || !Number.isFinite(value.access_token_expires_at)
  ) {
    return null;
  }
  return value;
}

async function loadTokenRecord(serviceUrl) {
  const serialized = await readSecret(serviceUrl);
  if (!serialized) return null;
  try {
    return validateTokenRecord(JSON.parse(serialized), serviceUrl);
  } catch {
    throw new SafeError(
      "Stored Webex credentials are invalid; run logout and authenticate again",
    );
  }
}

async function saveTokenRecord(serviceUrl, record) {
  await saveSecret(serviceUrl, JSON.stringify(record));
}

function normalizeTokenResponse(
  payload,
  serviceUrl,
  previous = null,
  clusterId = null,
) {
  if (!payload || typeof payload !== "object") {
    throw new SafeError("Webex token response is invalid");
  }
  if (typeof payload.access_token !== "string" || !payload.access_token) {
    throw new SafeError("Webex token response has no access token");
  }
  const refreshToken = (
    typeof payload.refresh_token === "string" && payload.refresh_token
  )
    ? payload.refresh_token
    : previous?.refresh_token;
  if (
    !refreshToken
    || !Number.isInteger(payload.expires_in)
    || payload.expires_in <= 0
  ) {
    throw new SafeError("Webex token response is incomplete");
  }
  const refreshChanged = Boolean(
    previous && refreshToken !== previous.refresh_token,
  );
  const refreshExpiry = Number.isInteger(payload.refresh_token_expires_in)
    ? Date.now() + payload.refresh_token_expires_in * 1000
    : refreshChanged
      ? null
      : previous?.refresh_token_expires_at ?? null;
  return {
    version: 2,
    service_url: serviceUrl,
    client_id: OAUTH_CLIENT_ID,
    cluster_id: clusterId ?? previous?.cluster_id ?? null,
    access_token: payload.access_token,
    refresh_token: refreshToken,
    token_type: typeof payload.token_type === "string"
      ? payload.token_type
      : "Bearer",
    scope: typeof payload.scope === "string"
      ? payload.scope
      : previous?.scope ?? "",
    access_token_expires_at: Date.now() + payload.expires_in * 1000,
    refresh_token_expires_at: refreshExpiry,
  };
}

export function generatePKCE() {
  const verifier = randomBytes(32).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  return { verifier, challenge };
}

export function generateState() {
  return randomBytes(16).toString("hex");
}

export function buildAuthorizeUrl(state, codeChallenge) {
  const params = new URLSearchParams({
    response_type: "code",
    client_id: OAUTH_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: OAUTH_SCOPES,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });
  return `${AUTHORIZE_URL}?${params.toString()}`;
}

// Webex auth codes look like `<base64>_<CLUSTER>_<orgId>`.
export function extractClusterId(code) {
  const match = /^[^_]+_([A-Z0-9]{4})_/.exec(code);
  return match ? match[1] : null;
}

export function tokenUrlFor(clusterId) {
  const base = CLUSTER_IDBROKER.get(clusterId) ?? DEFAULT_IDBROKER_URL;
  return `${base}/idb/oauth2/v1/access_token`;
}

export async function requestToken(form, clusterId) {
  const url = tokenUrlFor(clusterId);
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams(form).toString(),
      redirect: "error",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    throw classifyRequestFailure(url, error);
  }
  let payload = null;
  try {
    payload = JSON.parse(await response.text());
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const oauthError = typeof payload?.error === "string"
      && /^[a-z_]{1,64}$/.test(payload.error)
      ? `: ${payload.error}`
      : "";
    throw new SafeError(
      `Webex token request failed (HTTP ${response.status}${oauthError})`,
      { status: response.status, code: "oauth_error" },
    );
  }
  if (!payload || typeof payload !== "object") {
    throw new SafeError("Webex token response is invalid");
  }
  return payload;
}

const PAGE_STYLE = "font-family:system-ui;text-align:center;margin-top:20vh";
const SUCCESS_HTML = `<!DOCTYPE html><html><head><title>Webex login complete</title></head><body style="${PAGE_STYLE}"><h1>Login successful</h1><p>You can close this tab and return to your agent.</p></body></html>`;
const FAILURE_HTML = `<!DOCTYPE html><html><head><title>Webex login failed</title></head><body style="${PAGE_STYLE}"><h1>Login failed</h1><p>Return to your agent and try again.</p></body></html>`;

function stateMatches(expected, received) {
  if (typeof received !== "string") return false;
  const a = Buffer.from(expected);
  const b = Buffer.from(received);
  return a.length === b.length && timingSafeEqual(a, b);
}

// Resolves once listening; `code` settles when the browser hits the callback.
export async function startCallbackServer(
  expectedState,
  { port = CALLBACK_PORT, timeoutMs = LOGIN_TIMEOUT_MS } = {},
) {
  let resolveCode;
  let rejectCode;
  const code = new Promise((resolvePromise, rejectPromise) => {
    resolveCode = resolvePromise;
    rejectCode = rejectPromise;
  });
  let settled = false;
  let timer = null;

  const server = createServer((req, res) => {
    const url = new URL(req.url ?? "/", "http://localhost");
    if (url.pathname !== "/callback") {
      res.writeHead(404).end();
      return;
    }
    if (req.method !== "GET") {
      res.writeHead(405, { Allow: "GET" }).end();
      return;
    }
    const headers = {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      Connection: "close",
    };
    const error = url.searchParams.get("error");
    const received = url.searchParams.get("code");
    let failure = null;
    if (error) {
      failure = /^[a-z_]{1,64}$/.test(error)
        ? `Webex authorization failed: ${error}`
        : "Webex authorization failed";
    } else if (!stateMatches(expectedState, url.searchParams.get("state"))) {
      failure = "Webex authorization state mismatch";
    } else if (!received) {
      failure = "Webex authorization returned no code";
    }
    res.writeHead(200, headers);
    res.end(failure ? FAILURE_HTML : SUCCESS_HTML, () => {
      finish(failure ? new SafeError(failure) : null, received);
    });
  });

  function finish(error, value) {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    server.close();
    server.closeAllConnections();
    if (error) rejectCode(error);
    else resolveCode(value);
  }

  await new Promise((resolvePromise, rejectPromise) => {
    server.once("error", (error) => {
      rejectPromise(new SafeError(
        error?.code === "EADDRINUSE"
          ? `Port ${port} is already in use; close the other process and try again`
          : "Failed to start the local login callback server",
      ));
    });
    server.listen(port, "127.0.0.1", resolvePromise);
  });
  timer = setTimeout(() => {
    finish(new SafeError("Webex login timed out; run auth to try again"));
  }, timeoutMs);
  return { port: server.address().port, code };
}

export function shouldSuppressBrowser(env = process.env) {
  return Boolean(env.WEBEX_NO_BROWSER || env.GIT_DIR || env.CI);
}

async function openBrowser(url) {
  let command;
  let args;
  if (platform() === "darwin") {
    command = "/usr/bin/open";
    args = [url];
  } else if (platform() === "win32") {
    command = "rundll32.exe";
    args = ["url.dll,FileProtocolHandler", url];
  } else {
    command = "xdg-open";
    args = [url];
  }
  try {
    const result = await runProcess(command, args, { allowFailure: true });
    return result.code === 0;
  } catch {
    return false;
  }
}

// Fails fast (e.g. sandboxed network) before the user is sent to the browser.
async function checkIdbrokerReachable() {
  try {
    await fetch(DEFAULT_IDBROKER_URL, {
      method: "HEAD",
      redirect: "manual",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    throw classifyRequestFailure(DEFAULT_IDBROKER_URL, error);
  }
}

async function authenticate(serviceUrl) {
  await checkIdbrokerReachable();
  const { verifier, challenge } = generatePKCE();
  const state = generateState();
  const callback = await startCallbackServer(state);
  const authorizeUrl = buildAuthorizeUrl(state, challenge);

  process.stderr.write(
    `Webex authorization is required. Complete login at:\n${authorizeUrl}\n`,
  );
  if (shouldSuppressBrowser() || !await openBrowser(authorizeUrl)) {
    process.stderr.write(
      "The browser was not opened automatically; open the URL above manually.\n",
    );
  }

  const code = await callback.code;
  const clusterId = extractClusterId(code);
  const tokens = await requestToken(
    {
      grant_type: "authorization_code",
      client_id: OAUTH_CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
    },
    clusterId,
  );
  const record = normalizeTokenResponse(tokens, serviceUrl, null, clusterId);
  await saveTokenRecord(serviceUrl, record);
  return record;
}

async function refreshTokens(serviceUrl, previous) {
  const payload = await requestToken(
    {
      grant_type: "refresh_token",
      client_id: OAUTH_CLIENT_ID,
      refresh_token: previous.refresh_token,
    },
    previous.cluster_id,
  );
  const record = normalizeTokenResponse(payload, serviceUrl, previous);
  await saveTokenRecord(serviceUrl, record);
  return record;
}

function accessTokenUsable(record) {
  return Boolean(
    record && record.access_token_expires_at > Date.now() + TOKEN_SKEW_MS,
  );
}

function refreshTokenUsable(record) {
  return Boolean(
    record
    && (
      !record.refresh_token_expires_at
      || record.refresh_token_expires_at > Date.now() + TOKEN_SKEW_MS
    ),
  );
}

async function ensureTokens(
  serviceUrl,
  { forceAuth = false, forceRefresh = false } = {},
) {
  if (forceAuth) return authenticate(serviceUrl);
  const record = await loadTokenRecord(serviceUrl);
  if (!forceRefresh && accessTokenUsable(record)) return record;
  if (refreshTokenUsable(record)) {
    try {
      return await refreshTokens(serviceUrl, record);
    } catch (error) {
      if (
        !(error instanceof SafeError)
        || (error.status !== 400 && error.status !== 401)
      ) {
        throw error;
      }
    }
  }
  return authenticate(serviceUrl);
}

export function validateSearchRequest(value) {
  if (!value || typeof value !== "object" || !Array.isArray(value.queries)) {
    throw new SafeError("Search request must contain a queries array");
  }
  if (value.queries.length < 1 || value.queries.length > 8) {
    throw new SafeError("Search request must contain between 1 and 8 queries");
  }
  const seen = new Set();
  const queries = value.queries.map((query) => {
    if (
      typeof query !== "string"
      || !query.trim()
      || query.trim().length > 500
    ) {
      throw new SafeError(
        "Each query must be a non-empty string of at most 500 characters",
      );
    }
    const normalized = query.trim();
    const key = normalized.toLocaleLowerCase();
    if (seen.has(key)) {
      throw new SafeError("Search queries must be distinct");
    }
    seen.add(key);
    return normalized;
  });

  const sources = value.sources === undefined ? ["docs", "api"] : value.sources;
  if (
    !Array.isArray(sources)
    || sources.length < 1
    || sources.length > 2
    || sources.some((source) => !["docs", "api"].includes(source))
    || new Set(sources).size !== sources.length
  ) {
    throw new SafeError("sources must contain distinct docs and/or api values");
  }
  if (
    value.filter !== undefined
    && value.filter !== null
    && !["webex_suite", "cc"].includes(value.filter)
  ) {
    throw new SafeError("filter must be webex_suite or cc");
  }
  const maxResults = value.max_results_per_source === undefined
    ? 5
    : value.max_results_per_source;
  if (!Number.isInteger(maxResults) || maxResults < 1 || maxResults > 10) {
    throw new SafeError(
      "max_results_per_source must be an integer from 1 to 10",
    );
  }
  return {
    queries,
    sources,
    ...(value.filter === undefined || value.filter === null
      ? {}
      : { filter: value.filter }),
    max_results_per_source: maxResults,
  };
}

async function readSearchRequest(args) {
  const requestIndex = args.indexOf("--request");
  let serialized;
  if (requestIndex !== -1) {
    const path = args[requestIndex + 1];
    if (!path) throw new SafeError("--request requires a JSON file path");
    serialized = await readFile(resolve(path), "utf8");
  } else if (!process.stdin.isTTY) {
    const chunks = [];
    for await (const chunk of process.stdin) chunks.push(chunk);
    serialized = Buffer.concat(chunks).toString("utf8");
  } else {
    throw new SafeError(
      "Provide search JSON through --request or standard input",
    );
  }
  try {
    return validateSearchRequest(JSON.parse(serialized));
  } catch (error) {
    if (error instanceof SafeError) throw error;
    throw new SafeError("Search request is not valid JSON");
  }
}

async function search(serviceUrl, request) {
  let record = await ensureTokens(serviceUrl);
  const call = () => requestJson(
    serviceUrl,
    `${API_PREFIX}/knowledge/search`,
    {
      method: "POST",
      headers: {
        Authorization: `${record.token_type || "Bearer"} ${record.access_token}`,
      },
      body: request,
    },
  );
  try {
    return (await call()).payload;
  } catch (error) {
    if (!(error instanceof SafeError) || error.status !== 401) throw error;
    record = await ensureTokens(serviceUrl, { forceRefresh: true });
    return (await call()).payload;
  }
}

function safeStatus(record, serviceUrl) {
  return {
    service_url: serviceUrl,
    authenticated: Boolean(record),
    access_token_usable: accessTokenUsable(record),
    refresh_token_usable: refreshTokenUsable(record),
    access_token_expires_at: record
      ? new Date(record.access_token_expires_at).toISOString()
      : null,
    refresh_token_expires_at: record?.refresh_token_expires_at
      ? new Date(record.refresh_token_expires_at).toISOString()
      : null,
    scope: record?.scope || "",
  };
}

function printJson(value) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

export async function main(argv = process.argv.slice(2)) {
  const command = argv[0];
  const serviceUrl = resolveServiceUrl();
  if (command === "search") {
    const request = await readSearchRequest(argv.slice(1));
    printJson(await search(serviceUrl, request));
    return;
  }
  if (command === "auth") {
    const record = await ensureTokens(serviceUrl, { forceAuth: true });
    printJson(safeStatus(record, serviceUrl));
    return;
  }
  if (command === "status") {
    printJson(safeStatus(await loadTokenRecord(serviceUrl), serviceUrl));
    return;
  }
  if (command === "logout") {
    await deleteSecret(serviceUrl);
    printJson({ service_url: serviceUrl, authenticated: false });
    return;
  }
  throw new SafeError(
    "Usage: webex-knowledge.mjs <auth|status|search|logout> [--request path]",
  );
}

const invokedPath = process.argv[1]
  ? pathToFileURL(resolve(process.argv[1])).href
  : null;
if (invokedPath === import.meta.url) {
  main().catch((error) => {
    const payload = {
      error: error instanceof SafeError
        ? error.message
        : "Webex knowledge helper failed",
      ...(error instanceof SafeError && error.status
        ? { status: error.status }
        : {}),
      ...(error instanceof SafeError && error.code
        ? { code: error.code }
        : {}),
    };
    process.stderr.write(`${JSON.stringify(payload)}\n`);
    process.exitCode = 1;
  });
}
