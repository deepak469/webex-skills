import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { homedir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  OAUTH_CLIENT_ID,
  REDIRECT_URI,
  SERVICE_URL,
  buildAuthorizeUrl,
  classifyRequestFailure,
  extractClusterId,
  generatePKCE,
  macOSKeychainSaveArgs,
  main,
  requestToken,
  resolveServiceUrl,
  shouldSuppressBrowser,
  startCallbackServer,
  tokenUrlFor,
  validateSearchRequest,
} from "../skill/webex-api-knowledge/scripts/webex-knowledge.mjs";
import { installationTargets, parseArguments } from "../scripts/install-skill.mjs";

async function withFetch(stub, run) {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = stub;
  try {
    return await run();
  } finally {
    globalThis.fetch = originalFetch;
  }
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

test("builds an S256 PKCE authorize URL for the public client", () => {
  const { verifier, challenge } = generatePKCE();
  assert.match(verifier, /^[A-Za-z0-9_-]{43}$/);
  assert.equal(
    challenge,
    createHash("sha256").update(verifier).digest("base64url"),
  );

  const url = new URL(buildAuthorizeUrl("state-fixture", challenge));
  assert.equal(url.origin + url.pathname, "https://idbroker.webex.com/idb/oauth2/v1/authorize");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    response_type: "code",
    client_id: OAUTH_CLIENT_ID,
    redirect_uri: "http://localhost:17177/callback",
    scope: "identity:people_read spark:mcp",
    state: "state-fixture",
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
});

test("routes token requests to the code's cluster idbroker", () => {
  assert.equal(extractClusterId("YWJj_PE93_org-id"), "PE93");
  assert.equal(extractClusterId("no-cluster"), null);
  assert.equal(
    tokenUrlFor("PE93"),
    "https://idbroker-eu.webex.com/idb/oauth2/v1/access_token",
  );
  assert.equal(
    tokenUrlFor("ZZZZ"),
    "https://idbroker.webex.com/idb/oauth2/v1/access_token",
  );
  assert.equal(
    tokenUrlFor(null),
    "https://idbroker.webex.com/idb/oauth2/v1/access_token",
  );
});

test("exchanges the code without a client secret", async () => {
  let captured;
  const tokens = await withFetch(async (url, init) => {
    captured = { url, init };
    return new Response(JSON.stringify({ access_token: "a", expires_in: 1 }));
  }, () => requestToken(
    {
      grant_type: "authorization_code",
      client_id: OAUTH_CLIENT_ID,
      code: "YWJj_PE93_org",
      redirect_uri: REDIRECT_URI,
      code_verifier: "verifier",
    },
    "PE93",
  ));
  assert.equal(tokens.access_token, "a");
  assert.equal(
    captured.url,
    "https://idbroker-eu.webex.com/idb/oauth2/v1/access_token",
  );
  const form = new URLSearchParams(captured.init.body);
  assert.equal(form.get("code_verifier"), "verifier");
  assert.equal(form.has("client_secret"), false);
});

test("reports OAuth errors without echoing the response body", async () => {
  await withFetch(
    async () => new Response(
      JSON.stringify({ error: "invalid_grant", error_description: "secret-ish detail" }),
      { status: 400 },
    ),
    () => assert.rejects(
      () => requestToken({ grant_type: "refresh_token" }, null),
      (error) => error.status === 400
        && /invalid_grant/.test(error.message)
        && !/secret-ish/.test(error.message),
    ),
  );
});

test("callback server accepts only the expected state", async () => {
  const ok = await startCallbackServer("expected", { port: 0 });
  const okResponse = await fetch(
    `http://127.0.0.1:${ok.port}/callback?code=the-code&state=expected`,
  );
  assert.equal(okResponse.status, 200);
  assert.equal(await ok.code, "the-code");

  const bad = await startCallbackServer("expected", { port: 0 });
  const rejected = assert.rejects(bad.code, /state mismatch/);
  await fetch(`http://127.0.0.1:${bad.port}/callback?code=x&state=other`);
  await rejected;

  const denied = await startCallbackServer("expected", { port: 0 });
  const deniedResult = assert.rejects(denied.code, /access_denied/);
  await fetch(`http://127.0.0.1:${denied.port}/callback?error=access_denied`);
  await deniedResult;
});

test("suppresses the browser in non-interactive contexts", () => {
  assert.equal(shouldSuppressBrowser({}), false);
  assert.equal(shouldSuppressBrowser({ CI: "true" }), true);
  assert.equal(shouldSuppressBrowser({ GIT_DIR: ".git" }), true);
  assert.equal(shouldSuppressBrowser({ WEBEX_NO_BROWSER: "1" }), true);
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
