#!/usr/bin/env node
// Generate the shared plugin and skill catalog from manifests and SKILL.md files.

import { writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { inspectPlugins, renderCatalog } from "./lib/plugins.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const { plugins, errors } = inspectPlugins(ROOT);
if (errors.length) {
  process.stderr.write(`Cannot generate catalog until plugin validation issues are fixed:\n${errors.map((error) => `  - ${error}`).join("\n")}\n`);
  process.exitCode = 1;
} else {
  const catalog = renderCatalog(plugins);
  writeFileSync(join(ROOT, "catalog.json"), catalog.json);
  writeFileSync(join(ROOT, "PLUGINS.md"), catalog.markdown);
  process.stdout.write(`Generated catalog.json and PLUGINS.md for ${plugins.length} plugin(s).\n`);
}
