#!/usr/bin/env node
// Usage: node scripts/package-skill.mjs <skill-name> [--dry-run]
// Packs the skill into skills/<name>/release/ and prints the result as JSON.

import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { REPO_ROOT, readPackage, skillDirectory } from "./lib/skills.mjs";
import { assertChangelog } from "./lib/changelog.mjs";

const [name, ...flags] = process.argv.slice(2);
const dryRun = flags.includes("--dry-run");

const directory = skillDirectory(name);
const { name: packageName, version } = readPackage(name);
const releaseDirectory = join(directory, "release");
// npm pack names scoped packages "<scope>-<name>-<version>.tgz".
const packageBase = packageName.replace(/^@/, "").replace("/", "-");
const expectedFile = `${packageBase}-${version}.tgz`;
// Stable file name so install commands never need a version bump.
const latestFile = `${packageBase}-latest.tgz`;

if (existsSync(join(releaseDirectory, expectedFile))) {
  throw new Error(
    `${name}@${version} is already released (${expectedFile}). Bump "version" in skills/${name}/package.json.`,
  );
}
assertChangelog(name, version);

mkdirSync(releaseDirectory, { recursive: true });
const args = ["pack", "--json", "--pack-destination", releaseDirectory];
if (dryRun) args.push("--dry-run");
const [result] = JSON.parse(
  execFileSync("npm", args, { cwd: directory, encoding: "utf8", shell: process.platform === "win32" }),
);

if (!dryRun) copyFileSync(join(releaseDirectory, result.filename), join(releaseDirectory, latestFile));

const output = {
  skill: name,
  package: packageName,
  version,
  dryRun,
  file: relative(REPO_ROOT, join(releaseDirectory, result.filename)),
  latest: relative(REPO_ROOT, join(releaseDirectory, latestFile)),
  files: result.files.map((file) => file.path),
  releases: readdirSync(releaseDirectory).filter((file) => file.endsWith(".tgz")),
};
process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
