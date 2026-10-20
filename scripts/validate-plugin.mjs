#!/usr/bin/env node
// Validate every plugin, supported marketplace entry, and generated catalog.

import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { inspectPlugins, renderCatalog } from "./lib/plugins.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const { plugins, errors } = inspectPlugins(ROOT);
const expected = renderCatalog(plugins);

for (const [path, content] of [
  ["catalog.json", expected.json],
  ["PLUGINS.md", expected.markdown],
]) {
  const fullPath = join(ROOT, path);
  if (!existsSync(fullPath)) {
    errors.push(`${path} is missing; run node scripts/generate-catalog.mjs`);
  } else if (readFileSync(fullPath, "utf8") !== content) {
    errors.push(`${path} is out of date; run node scripts/generate-catalog.mjs and commit the result`);
  }
}

if (errors.length) {
  process.stderr.write(`✗ plugin validation\n${errors.map((error) => `  - ${error}`).join("\n")}\n`);
  process.exitCode = 1;
} else {
  for (const plugin of plugins) {
    process.stdout.write(`✓ ${plugin.name} (${plugin.skills.length} skills; ${plugin.surfaces.join(", ")})\n`);
  }
}
