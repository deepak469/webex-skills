import { existsSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { REPO_ROOT, skillDirectory } from "./skills.mjs";

const STABLE_VERSION = /^\d+\.\d+\.\d+$/;

export const isStable = (version) => STABLE_VERSION.test(version || "");

export function compareVersions(a, b) {
  const [left, right] = [a, b].map((version) => version.split(".").map(Number));
  for (let index = 0; index < 3; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index];
  }
  return 0;
}

export function changelogPath(name) {
  return join(skillDirectory(name), "release", "CHANGELOG.md");
}

export function changelogEntry(name, version) {
  const path = changelogPath(name);
  if (!existsSync(path)) return null;
  const lines = readFileSync(path, "utf8").split(/\r?\n/);
  const heading = new RegExp(`^## \\[?${version.replaceAll(".", "\\.")}\\]?(\\s|$)`);
  const start = lines.findIndex((line) => heading.test(line));
  if (start === -1) return null;
  const end = lines.findIndex((line, index) => index > start && line.startsWith("## "));
  const body = lines.slice(start + 1, end === -1 ? undefined : end).join("\n").trim();
  return /^\s*[-*] \S/m.test(body) ? body : null;
}

export function assertChangelog(name, version) {
  if (!isStable(version) || changelogEntry(name, version)) return;
  const path = relative(REPO_ROOT, changelogPath(name));
  throw new Error(
    [
      `${name}@${version} is a stable version, but ${path} has no entry for ${version}.`,
      "A changelog entry is required before packaging a stable release.",
      `Use the project skill "skill-changelog" to create it, e.g. ask your agent: "use skill-changelog to prepare the ${name} ${version} changelog".`,
      "It drafts the entry from commits, opens a changelog PR; merge that PR, then rerun this workflow.",
    ].join("\n"),
  );
}
