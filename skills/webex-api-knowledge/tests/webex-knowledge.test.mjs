import assert from "node:assert/strict";
import { homedir } from "node:os";
import { join } from "node:path";
import {
  createCipheriv,
  diffieHellman,
  generateKeyPairSync,
  hkdfSync,
  randomBytes,
} from "node:crypto";
import test from "node:test";

import {
  SERVICE_URL,
  classifyRequestFailure,
  decryptTokenEnvelope,
  macOSKeychainSaveArgs,
  main,
  resolveServiceUrl,
  validateSearchRequest,
} from "../skill/webex-api-knowledge/scripts/webex-knowledge.mjs";
import { installationTargets, parseArguments } from "../scripts/install-skill.mjs";

const X25519_SPKI_PREFIX = Buffer.from("302a300506032b656e032100", "hex");

function rawPublicKey(publicKey) {
  const spki = Buffer.from(publicKey.export({ format: "der", type: "spki" }));
  assert.deepEqual(spki.subarray(0, X25519_SPKI_PREFIX.length), X25519_SPKI_PREFIX);
  return spki.subarray(X25519_SPKI_PREFIX.length);
}

function encryptedFixture(sessionId, clientPublicKey, tokens) {
  const server = generateKeyPairSync("x25519");
  const sharedSecret = diffieHellman({
    privateKey: server.privateKey,
    publicKey: clientPublicKey,
  });
  const salt = randomBytes(16);
  const nonce = randomBytes(12);
  const key = Buffer.from(hkdfSync(
    "sha256",
    sharedSecret,
    salt,
    Buffer.from(`webex-knowledge-oauth:${sessionId}`),
    32,
  ));
  const cipher = createCipheriv("aes-256-gcm", key, nonce);
  cipher.setAAD(Buffer.from(sessionId));
  const encrypted = Buffer.concat([
    cipher.update(JSON.stringify(tokens)),
    cipher.final(),
  ]);
  const ciphertext = Buffer.concat([encrypted, cipher.getAuthTag()]);
  return {
    algorithm: "X25519-HKDF-SHA256-AESGCM",
    server_public_key: rawPublicKey(server.publicKey).toString("base64url"),
    salt: salt.toString("base64url"),
    nonce: nonce.toString("base64url"),
    ciphertext: ciphertext.toString("base64url"),
  };
}

test("uses only the fixed integration origin", () => {
  assert.equal(
    SERVICE_URL,
    "https://webex-developer-ai-assistant-intb.ciscospark.com",
  );
  assert.equal(resolveServiceUrl(), SERVICE_URL);
});

test("classifies a failed sandboxed request as requiring permission", () => {
  const blocked = classifyRequestFailure(
    SERVICE_URL,
    new TypeError("fetch failed"),
    { CODEX_SANDBOX_NETWORK_DISABLED: "1" },
  );
  assert.equal(blocked.code, "network_permission_required");
  assert.match(
    blocked.message,
    /shell execution tool's sandbox\/network escalation/,
  );

  const ordinary = classifyRequestFailure(
    SERVICE_URL,
    new TypeError("fetch failed"),
    {},
  );
  assert.equal(ordinary.code, "service_unavailable");

  const timeout = classifyRequestFailure(
    SERVICE_URL,
    Object.assign(new Error("timed out"), { name: "TimeoutError" }),
    { CODEX_SANDBOX_NETWORK_DISABLED: "1" },
  );
  assert.equal(timeout.code, "service_unavailable");
  assert.match(timeout.message, /timed out/);
});

test("network classification does not block a request before fetch", async () => {
  const originalFetch = globalThis.fetch;
  let called = false;
  globalThis.fetch = async () => {
    called = true;
    throw new TypeError("fetch failed");
  };
  const previous = process.env.CODEX_SANDBOX_NETWORK_DISABLED;
  process.env.CODEX_SANDBOX_NETWORK_DISABLED = "1";
  try {
    await assert.rejects(
      () => main(["auth"]),
      (error) => error.code === "network_permission_required",
    );
    assert.equal(called, true);
  } finally {
    globalThis.fetch = originalFetch;
    if (previous === undefined) {
      delete process.env.CODEX_SANDBOX_NETWORK_DISABLED;
    } else {
      process.env.CODEX_SANDBOX_NETWORK_DISABLED = previous;
    }
  }
});

test("supplies macOS Keychain password data non-interactively", () => {
  const secret = '{"access_token":"fixture"}';
  const args = macOSKeychainSaveArgs(
    { account: "developer", service: "com.cisco.webex.fixture" },
    secret,
  );

  assert.deepEqual(args, [
    "add-generic-password",
    "-U",
    "-a",
    "developer",
    "-s",
    "com.cisco.webex.fixture",
    "-w",
    secret,
  ]);
  assert.equal(args.at(-2), "-w");
  assert.equal(args.at(-1), secret);
});

test("normalizes a bounded search request", () => {
  assert.deepEqual(
    validateSearchRequest({
      queries: ["  create a meeting  ", "list meeting participants"],
      filter: "webex_suite",
    }),
    {
      queries: ["create a meeting", "list meeting participants"],
      sources: ["docs", "api"],
      filter: "webex_suite",
      max_results_per_source: 5,
    },
  );
});

test("rejects duplicate and oversized search requests", () => {
  assert.throws(
    () => validateSearchRequest({ queries: ["Meetings", " meetings "] }),
    /must be distinct/,
  );
  assert.throws(
    () => validateSearchRequest({ queries: Array.from({ length: 9 }, (_, index) => `q${index}`) }),
    /between 1 and 8/,
  );
});

test("decrypts the server-compatible token envelope", () => {
  const client = generateKeyPairSync("x25519");
  const sessionId = "f37f1472-56b2-4ee7-bddb-5fb22c7fc91e";
  const tokens = {
    access_token: "access-token-fixture",
    refresh_token: "refresh-token-fixture",
    token_type: "Bearer",
    expires_in: 3600,
    scope: "spark:mcp identity:people_read",
  };
  const envelope = encryptedFixture(sessionId, client.publicKey, tokens);

  assert.deepEqual(
    decryptTokenEnvelope(sessionId, client.privateKey, envelope),
    tokens,
  );

  const tampered = {
    ...envelope,
    ciphertext: `${envelope.ciphertext.slice(0, -2)}AA`,
  };
  assert.throws(
    () => decryptTokenEnvelope(sessionId, client.privateKey, tampered),
    /authentication failed/,
  );
});

test("shares the project installation between Codex and Copilot", () => {
  assert.deepEqual(
    installationTargets("all", "project", "/workspace"),
    [
      "/workspace/.agents/skills/webex-api-knowledge",
      "/workspace/.claude/skills/webex-api-knowledge",
    ],
  );
});

test("installs user-level copies for all three clients", () => {
  assert.deepEqual(
    installationTargets("all", "user"),
    [
      join(homedir(), ".agents", "skills", "webex-api-knowledge"),
      join(homedir(), ".copilot", "skills", "webex-api-knowledge"),
      join(homedir(), ".claude", "skills", "webex-api-knowledge"),
    ],
  );
});

test("accepts npm-style and direct installer arguments", () => {
  const expected = {
    client: "all",
    scope: "user",
    force: true,
    help: false,
  };
  assert.deepEqual(
    parseArguments([
      "install",
      "--client",
      "all",
      "--scope",
      "user",
      "--force",
    ]),
    expected,
  );
  assert.deepEqual(
    parseArguments([
      "--client",
      "all",
      "--scope",
      "user",
      "--force",
    ]),
    expected,
  );
  assert.throws(
    () => parseArguments(["publish", "--client", "all", "--scope", "user"]),
    /Usage:/,
  );
});
