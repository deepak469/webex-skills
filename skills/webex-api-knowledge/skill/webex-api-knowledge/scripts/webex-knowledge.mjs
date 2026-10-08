#!/usr/bin/env node

import {
  createDecipheriv,
  createHash,
  createPublicKey,
  diffieHellman,
  generateKeyPairSync,
  hkdfSync,
} from "node:crypto";
import { spawn } from "node:child_process";
import { mkdir, readFile, rm } from "node:fs/promises";
import { homedir, platform, userInfo } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const SERVICE_URL =
  "https://webex-developer-ai-assistant-intb.ciscospark.com";
const API_PREFIX = "/webex-developer-ai-assistant/api/v1";
const TOKEN_SKEW_MS = 60_000;
const REQUEST_TIMEOUT_MS = 20_000;
const X25519_SPKI_PREFIX = Buffer.from("302a300506032b656e032100", "hex");

class SafeError extends Error {
  constructor(message, { status = null, code = null } = {}) {
    super(message);
    this.name = "SafeError";
    this.status = status;
    this.code = code;
  }
}

function base64urlEncode(value) {
  return Buffer.from(value).toString("base64url");
}

function base64urlDecode(value, field) {
  if (typeof value !== "string" || !value) {
    throw new SafeError(`Token envelope field ${field} is missing`);
  }
  try {
    return Buffer.from(value, "base64url");
  } catch {
    throw new SafeError(`Token envelope field ${field} is invalid`);
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
  serviceUrl,
  error,
  env = process.env,
) {
  if (
    env.CODEX_SANDBOX_NETWORK_DISABLED === "1"
    && error?.name !== "TimeoutError"
  ) {
    const host = new URL(serviceUrl).host;
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
  return new SafeError(`Knowledge service ${reason}`, {
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
  if (!value || typeof value !== "object" || value.service_url !== serviceUrl) {
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

function normalizeTokenResponse(payload, serviceUrl, previous = null) {
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
    version: 1,
    service_url: serviceUrl,
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

export function decryptTokenEnvelope(sessionId, privateKey, envelope) {
  if (
    !envelope
    || envelope.algorithm !== "X25519-HKDF-SHA256-AESGCM"
  ) {
    throw new SafeError("Unsupported token envelope algorithm");
  }
  const serverRaw = base64urlDecode(
    envelope.server_public_key,
    "server_public_key",
  );
  const salt = base64urlDecode(envelope.salt, "salt");
  const nonce = base64urlDecode(envelope.nonce, "nonce");
  const encrypted = base64urlDecode(envelope.ciphertext, "ciphertext");
  if (
    serverRaw.length !== 32
    || nonce.length !== 12
    || encrypted.length <= 16
  ) {
    throw new SafeError(
      "Token envelope has invalid key, nonce, or ciphertext length",
    );
  }
  const serverPublicKey = createPublicKey({
    key: Buffer.concat([X25519_SPKI_PREFIX, serverRaw]),
    format: "der",
    type: "spki",
  });
  const sharedSecret = diffieHellman({
    privateKey,
    publicKey: serverPublicKey,
  });
  const key = Buffer.from(hkdfSync(
    "sha256",
    sharedSecret,
    salt,
    Buffer.from(`webex-knowledge-oauth:${sessionId}`),
    32,
  ));
  const tag = encrypted.subarray(encrypted.length - 16);
  const ciphertext = encrypted.subarray(0, encrypted.length - 16);
  const decipher = createDecipheriv("aes-256-gcm", key, nonce);
  decipher.setAAD(Buffer.from(sessionId));
  decipher.setAuthTag(tag);
  try {
    const plaintext = Buffer.concat([
      decipher.update(ciphertext),
      decipher.final(),
    ]);
    return JSON.parse(plaintext.toString("utf8"));
  } catch {
    throw new SafeError("Token envelope authentication failed");
  }
}

function createClientKeyPair() {
  const { publicKey, privateKey } = generateKeyPairSync("x25519");
  const spki = Buffer.from(publicKey.export({ format: "der", type: "spki" }));
  const expectedLength = X25519_SPKI_PREFIX.length + 32;
  if (
    spki.length !== expectedLength
    || !spki.subarray(0, X25519_SPKI_PREFIX.length).equals(X25519_SPKI_PREFIX)
  ) {
    throw new SafeError("Unable to export the ephemeral X25519 public key");
  }
  return {
    privateKey,
    publicKeyRaw: spki.subarray(X25519_SPKI_PREFIX.length),
  };
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
  const result = await runProcess(command, args, { allowFailure: true });
  return result.code === 0;
}

function sleep(milliseconds) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, milliseconds));
}

async function authenticate(serviceUrl) {
  const { privateKey, publicKeyRaw } = createClientKeyPair();
  const { payload: session } = await requestJson(
    serviceUrl,
    `${API_PREFIX}/auth/webex/sessions`,
    {
      method: "POST",
      body: { client_public_key: base64urlEncode(publicKeyRaw) },
    },
  );
  if (
    !session
    || typeof session.session_id !== "string"
    || typeof session.poll_token !== "string"
    || typeof session.authorization_url !== "string"
  ) {
    throw new SafeError("OAuth session response is incomplete");
  }

  process.stderr.write(
    `Webex authorization is required. Complete login at:\n${session.authorization_url}\n`,
  );
  if (!await openBrowser(session.authorization_url)) {
    process.stderr.write(
      "The browser could not be opened automatically; open the URL above manually.\n",
    );
  }

  const lifetimeSeconds = Math.max(1, Number(session.expires_in) || 600);
  const deadline = Date.now() + lifetimeSeconds * 1000;
  let intervalMs = Math.max(1, Number(session.poll_interval) || 2) * 1000;
  while (Date.now() < deadline) {
    await sleep(intervalMs);
    const pickup = await requestJson(
      serviceUrl,
      `${API_PREFIX}/auth/webex/sessions/${encodeURIComponent(session.session_id)}/token`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${session.poll_token}` },
      },
    );
    if (pickup.status === 202) {
      const retryAfter = Number(
        pickup.payload?.retry_after || pickup.headers.get("retry-after") || 2,
      );
      intervalMs = Math.max(1, retryAfter) * 1000;
      continue;
    }
    const payload = pickup.payload;
    if (!payload || payload.status !== "ready" || !payload.token_envelope) {
      throw new SafeError("OAuth token pickup response is invalid");
    }
    const tokens = decryptTokenEnvelope(
      session.session_id,
      privateKey,
      payload.token_envelope,
    );
    const record = normalizeTokenResponse(tokens, serviceUrl);
    await saveTokenRecord(serviceUrl, record);
    return record;
  }
  throw new SafeError(
    "Webex authorization session expired before login completed",
  );
}

async function refreshTokens(serviceUrl, previous) {
  const { payload } = await requestJson(
    serviceUrl,
    `${API_PREFIX}/auth/webex/token/refresh`,
    {
      method: "POST",
      body: { refresh_token: previous.refresh_token },
    },
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
      if (!(error instanceof SafeError) || error.status !== 401) throw error;
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
