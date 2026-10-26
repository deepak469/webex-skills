import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

test("webexconnect-apple-messages-for-business-sendmessage package contains a named skill with frontmatter", async () => {
  const text = await readFile(new URL("../skill/webexconnect-apple-messages-for-business-sendmessage/SKILL.md", import.meta.url), "utf8");
  assert.match(text, /^---\r?\n[\s\S]*?name: webexconnect-apple-messages-for-business-sendmessage[\s\S]*?description:/);
});
