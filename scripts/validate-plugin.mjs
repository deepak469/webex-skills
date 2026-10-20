#!/usr/bin/env node
// Validate the Webex Connect AI plugin package and its marketplace manifests.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PLUGIN = join(ROOT, "plugins", "webex-connect-ai");
const errors = [];

function readJson(path) {
  if (!existsSync(path)) {
    errors.push(`${relative(path)} is missing`);
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    errors.push(`${relative(path)} is not valid JSON: ${error.message}`);
    return null;
  }
}

function relative(path) {
  return path.startsWith(`${ROOT}/`) ? path.slice(ROOT.length + 1) : path;
}

function requireFile(path, label) {
  if (!existsSync(path) || !statSync(path).isFile()) errors.push(`${label} is missing`);
}

function checkAsset(value, label) {
  if (typeof value !== "string" || !value.startsWith("./")) {
    errors.push(`${label} must be a relative path beginning with ./`);
    return;
  }
  const target = resolve(PLUGIN, value);
  if (!target.startsWith(`${PLUGIN}/`) || !existsSync(target) || !statSync(target).isFile()) {
    errors.push(`${label} points to a missing or out-of-package file: ${value}`);
  }
}

function checkMarketplace(path, sourceKind, version) {
  const marketplace = readJson(path);
  if (!marketplace) return;
  const entries = Array.isArray(marketplace.plugins)
    ? marketplace.plugins.filter((entry) => entry?.name === "webex-connect-ai")
    : [];
  if (entries.length !== 1) {
    errors.push(`${relative(path)} must contain exactly one webex-connect-ai entry`);
    return;
  }
  const entry = entries[0];
  if (entry.version !== version) errors.push(`${relative(path)} version must match ${version}`);
  if (sourceKind === "codex") {
    if (JSON.stringify(entry.source) !== JSON.stringify({ source: "local", path: "./plugins/webex-connect-ai" })) {
      errors.push(`${relative(path)} must point to ./plugins/webex-connect-ai as a local source`);
    }
  } else if (entry.source !== "./plugins/webex-connect-ai") {
    errors.push(`${relative(path)} source must be ./plugins/webex-connect-ai`);
  }
}

const codex = readJson(join(PLUGIN, ".codex-plugin", "plugin.json"));
const claude = readJson(join(PLUGIN, ".claude-plugin", "plugin.json"));
const cursor = readJson(join(PLUGIN, ".cursor-plugin", "plugin.json"));
const version = codex?.version;

for (const [label, manifest] of [["Codex", codex], ["Claude", claude], ["Cursor", cursor]]) {
  if (!manifest) continue;
  if (manifest.name !== "webex-connect-ai") errors.push(`${label} manifest name must be webex-connect-ai`);
  if (!manifest.version || manifest.version !== version) errors.push(`${label} manifest version must match ${version}`);
  if (typeof manifest.description !== "string" || !manifest.description.trim()) {
    errors.push(`${label} manifest description is required`);
  }
}

if (codex) {
  if (codex.skills !== "./skills/") errors.push("Codex manifest skills must be ./skills/");
  checkAsset(codex.interface?.logo, "Codex interface.logo");
  checkAsset(codex.interface?.composerIcon, "Codex interface.composerIcon");
}
if (claude && claude.commands !== "./commands/") errors.push("Claude manifest commands must be ./commands/");
if (cursor) {
  if (cursor.skills !== "./skills/") errors.push("Cursor manifest skills must be ./skills/");
  if (cursor.rules !== "./rules/") errors.push("Cursor manifest rules must be ./rules/");
  if (cursor.commands !== "./commands/") errors.push("Cursor manifest commands must be ./commands/");
  checkAsset(cursor.logo, "Cursor logo");
}

const skillRoot = join(PLUGIN, "skills");
const skills = existsSync(skillRoot)
  ? readdirSync(skillRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory())
  : [];
if (skills.length !== 19) errors.push(`expected 19 plugin skills, found ${skills.length}`);
for (const skill of skills) {
  const file = join(skillRoot, skill.name, "SKILL.md");
  requireFile(file, `${relative(file)} SKILL.md`);
  if (!existsSync(file)) continue;
  const text = readFileSync(file, "utf8");
  const frontmatter = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!frontmatter) {
    errors.push(`${relative(file)} is missing YAML frontmatter`);
    continue;
  }
  const name = frontmatter[1].match(/^name:\s*["']?([^\s"']+)/m)?.[1];
  if (name !== skill.name) errors.push(`${relative(file)} name must match its folder (${skill.name})`);
  if (!/^description:\s*\S/m.test(frontmatter[1])) errors.push(`${relative(file)} is missing a description`);
}

const forbiddenEnvFiles = [];
function scanForEnvFiles(directory) {
  if (!existsSync(directory)) return;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) scanForEnvFiles(path);
    else if (entry.name === ".env" || (entry.name.startsWith(".env.") && entry.name !== ".env.example")) {
      forbiddenEnvFiles.push(path);
    }
  }
}
scanForEnvFiles(PLUGIN);
for (const path of forbiddenEnvFiles) errors.push(`${relative(path)} must not be packaged`);

checkMarketplace(join(ROOT, ".agents", "plugins", "marketplace.json"), "codex", version);
checkMarketplace(join(ROOT, ".claude-plugin", "marketplace.json"), "claude", version);
checkMarketplace(join(ROOT, ".cursor-plugin", "marketplace.json"), "cursor", version);

if (errors.length) {
  process.stderr.write(`✗ webex-connect-ai plugin\n${errors.map((error) => `  - ${error}`).join("\n")}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`✓ webex-connect-ai plugin (${skills.length} skills, v${version})\n`);
}
