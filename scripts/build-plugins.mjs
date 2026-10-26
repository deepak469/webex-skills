#!/usr/bin/env node
// Assemble installable plugin folders from plugin.json skill links.

import { cp, mkdir, readdir, rm } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { inspectPlugins } from "./lib/plugins.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = join(ROOT, "dist", "plugins");
const selected = process.argv[2];
const { plugins, errors } = inspectPlugins(ROOT);
if (errors.length) throw new Error(`Cannot build plugins until validation issues are fixed:\n${errors.map((error) => `  - ${error}`).join("\n")}`);

const selectedPlugins = selected ? plugins.filter((plugin) => plugin.name === selected) : plugins;
if (selected && selectedPlugins.length === 0) throw new Error(`Unknown plugin: ${selected}`);

await mkdir(OUTPUT, { recursive: true });
for (const plugin of selectedPlugins) {
  const source = join(ROOT, "plugins", plugin.name);
  const target = join(OUTPUT, plugin.name);
  await rm(target, { recursive: true, force: true });
  await mkdir(target, { recursive: true });
  for (const entry of await readdir(source, { withFileTypes: true })) {
    if (entry.name === "plugin.json") continue;
    await cp(join(source, entry.name), join(target, entry.name), { recursive: true });
  }
  for (const skill of plugin.skills) {
    await cp(
      join(ROOT, "skills", skill.name, "skill", skill.name),
      join(target, "skills", skill.name),
      { recursive: true },
    );
  }
  process.stdout.write(`Built ${plugin.name} (${plugin.skills.length} linked skills) at ${join("dist", "plugins", plugin.name)}\n`);
}
