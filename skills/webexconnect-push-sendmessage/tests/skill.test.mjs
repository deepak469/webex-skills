import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

test("webexconnect-push-sendmessage package contains a named skill with frontmatter", async () => {
  const text = await readFile(new URL("../skill/webexconnect-push-sendmessage/SKILL.md", import.meta.url), "utf8");
  assert.match(text, /^---\r?\n[\s\S]*?name: webexconnect-push-sendmessage[\s\S]*?description:/);
});
