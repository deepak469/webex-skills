#!/usr/bin/env node
// Usage: node scripts/package-plugin.mjs <plugin-name> [--dry-run]
// Archives a committed plugin package into plugins/<name>/release/.

import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const [name, ...args] = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const NAME_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const VERSION_RE = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const STABLE_VERSION_RE = /^\d+\.\d+\.\d+$/;

if (!name || !NAME_RE.test(name)) throw new Error("Usage: node scripts/package-plugin.mjs <plugin-name> [--dry-run]");

const pluginRoot = join(ROOT, "plugins", name);
const packageRoot = join(ROOT, "plugin-packages", name);
const recipePath = join(pluginRoot, "plugin.json");
if (!existsSync(recipePath)) throw new Error(`Unknown plugin: ${name}`);
if (!existsSync(join(packageRoot, "plugin-lock.json"))) throw new Error(`Built package ${relative(ROOT, packageRoot)} is missing; run npm run plugin:build first`);

const recipe = JSON.parse(readFileSync(recipePath, "utf8"));
const { version } = recipe;
if (!VERSION_RE.test(version || "")) throw new Error(`${name}/plugin.json has an invalid version: ${version}`);
const releaseRoot = join(pluginRoot, "release");
const versionedName = `${name}-${version}.tgz`;
const latestName = `${name}-latest.tgz`;
const versionedPath = join(releaseRoot, versionedName);
const latestPath = join(releaseRoot, latestName);
if (existsSync(versionedPath)) throw new Error(`${name}@${version} is already packaged; bump the plugin version before releasing again`);
if (execFileSync("git", ["tag", "--list", `${name}@${version}`], { cwd: ROOT, encoding: "utf8" }).trim()) {
  throw new Error(`${name}@${version} is already tagged; bump the plugin version before releasing again`);
}

if (STABLE_VERSION_RE.test(version)) {
  const changelogPath = join(releaseRoot, "CHANGELOG.md");
  const changelog = existsSync(changelogPath) ? readFileSync(changelogPath, "utf8") : "";
  const escapedVersion = version.replaceAll(".", "\\.");
  const lines = changelog.split(/\r?\n/);
  const start = lines.findIndex((line) => new RegExp(`^## ${escapedVersion}(?:\\s|$)`).test(line));
  const end = lines.findIndex((line, index) => index > start && line.startsWith("## "));
  const entry = lines.slice(start + 1, end === -1 ? undefined : end).join("\n");
  if (start === -1 || !/^\s*[-*] \S/m.test(entry)) {
    throw new Error(`${relative(ROOT, changelogPath)} needs a non-empty entry for stable version ${version}`);
  }
}

const temporaryRoot = mkdtempSync(join(tmpdir(), "webex-plugin-release-"));
const temporaryArchive = join(temporaryRoot, versionedName);
try {
  execFileSync("tar", ["-czf", temporaryArchive, "-C", packageRoot, "."]);
  const files = execFileSync("tar", ["-tzf", temporaryArchive], { encoding: "utf8" }).trim().split("\n").filter(Boolean);
  if (!dryRun) {
    mkdirSync(releaseRoot, { recursive: true });
    copyFileSync(temporaryArchive, versionedPath);
    copyFileSync(temporaryArchive, latestPath);
  }
  process.stdout.write(`${JSON.stringify({
    plugin: name,
    version,
    dryRun,
    file: relative(ROOT, versionedPath),
    latest: relative(ROOT, latestPath),
    files,
  }, null, 2)}\n`);
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true });
}
