#!/usr/bin/env node
// Validate every plugin, supported marketplace entry, and generated catalog.

import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { inspectPlugins, renderCatalog, PLUGIN_PACKAGE_DIRECTORY } from "./lib/plugins.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const { plugins, errors } = inspectPlugins(ROOT);
const expected = renderCatalog(plugins);

for (const plugin of plugins) {
  const builtRoot = join(ROOT, PLUGIN_PACKAGE_DIRECTORY, plugin.name);
  if (!existsSync(builtRoot)) {
    errors.push(`${PLUGIN_PACKAGE_DIRECTORY}/${plugin.name} is missing; run npm run plugin:build and commit the generated package`);
    continue;
  }
  const sourceRoot = join(ROOT, "plugins", plugin.name);
  const lockPath = join(builtRoot, "plugin-lock.json");
  if (!existsSync(lockPath)) {
    errors.push(`${PLUGIN_PACKAGE_DIRECTORY}/${plugin.name}/plugin-lock.json is missing; rebuild the plugin package`);
  } else {
    try {
      const lock = JSON.parse(readFileSync(lockPath, "utf8"));
      const expectedSkills = Object.fromEntries(plugin.skills.map((skill) => [skill.name, skill.version]));
      if (lock.name !== plugin.name || lock.version !== plugin.version || JSON.stringify(lock.skills) !== JSON.stringify(expectedSkills)) {
        errors.push(`${PLUGIN_PACKAGE_DIRECTORY}/${plugin.name}/plugin-lock.json is out of date; rebuild the plugin package`);
      }
    } catch (error) {
      errors.push(`${PLUGIN_PACKAGE_DIRECTORY}/${plugin.name}/plugin-lock.json is invalid: ${error.message}`);
    }
  }
  for (const skill of plugin.skills) {
    if (!existsSync(join(builtRoot, "skills", skill.name, "SKILL.md"))) {
      errors.push(`${PLUGIN_PACKAGE_DIRECTORY}/${plugin.name}/skills/${skill.name}/SKILL.md is missing; rebuild the plugin package`);
    }
  }
  for (const [surface, manifestInfo] of plugin.manifests) {
    const relativeManifest = manifestInfo.path.slice(sourceRoot.length + 1);
    if (!existsSync(join(builtRoot, relativeManifest))) {
      errors.push(`${PLUGIN_PACKAGE_DIRECTORY}/${plugin.name}/${relativeManifest} is missing (${surface} manifest); rebuild the plugin package`);
    }
  }
}

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
