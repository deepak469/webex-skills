import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

test("webexconnect-ios-push-inapp-messaging-builder package contains a named skill with frontmatter", async () => {
  const text = await readFile(new URL("../skill/webexconnect-ios-push-inapp-messaging-builder/SKILL.md", import.meta.url), "utf8");
  assert.match(text, /^---\r?\n[\s\S]*?name: webexconnect-ios-push-inapp-messaging-builder[\s\S]*?description:/);
});
