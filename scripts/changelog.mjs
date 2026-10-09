#!/usr/bin/env node
// Usage: node scripts/changelog.mjs check <skill>
//        node scripts/changelog.mjs context <skill> [--version X.Y.Z]

import { execFileSync } from "node:child_process";
import { relative } from "node:path";
import { REPO_ROOT, readPackage } from "./lib/skills.mjs";
import { assertChangelog, changelogEntry, changelogPath, compareVersions, isStable } from "./lib/changelog.mjs";

const EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";

function git(...args) {
  return execFileSync("git", args, { cwd: REPO_ROOT, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).trim();
}

function context(name, requestedVersion) {
  const currentVersion = readPackage(name).version;
  const version = requestedVersion || currentVersion;
  if (!isStable(version)) {
    throw new Error(`Changelogs are only for stable versions (X.Y.Z); got "${version}". Pass --version X.Y.Z.`);
  }

  const released = git("tag", "--list", `${name}@*`)
    .split("\n")
    .filter(Boolean)
    .map((tag) => tag.slice(name.length + 1))
    .filter(isStable)
    .sort(compareVersions);
  if (released.includes(version)) throw new Error(`${name}@${version} is already tagged; choose a newer version.`);
  const previousVersion = released.filter((tagged) => compareVersions(tagged, version) < 0).pop() || null;
  const previousTag = previousVersion ? `${name}@${previousVersion}` : null;

  // Release artifacts are generated, so they are not part of the change history.
  const pathspec = ["--", `skills/${name}`, `:(exclude)skills/${name}/release`];
  const log = git("log", "--no-merges", "--format=%H%x1f%an%x1f%as%x1f%s%x1f%b%x1e", previousTag ? `${previousTag}..HEAD` : "HEAD", ...pathspec);
  const commits = log
    .split("\x1e")
    .map((record) => record.trim())
    .filter(Boolean)
    .map((record) => {
      const [sha, author, date, subject, body] = record.split("\x1f");
      return { sha: sha.slice(0, 10), author, date, subject, body: body?.trim() || "" };
    });
  const files = git("diff", "--name-status", previousTag || EMPTY_TREE, "HEAD", ...pathspec)
    .split("\n")
    .filter(Boolean);

  return {
    skill: name,
    currentVersion,
    version,
    versionBumpNeeded: currentVersion !== version,
    previousVersion,
    previousTag,
    tagsFound: released.length,
    range: previousTag ? `${previousTag}..HEAD` : "full history",
    changelog: relative(REPO_ROOT, changelogPath(name)),
    entryExists: Boolean(changelogEntry(name, version)),
    branch: `changelog/${name}-${version}`,
    commits,
    files,
  };
}

const [command, name, ...rest] = process.argv.slice(2);
try {
  if (command === "check") {
    const { version } = readPackage(name);
    assertChangelog(name, version);
    process.stdout.write(isStable(version) ? `✓ changelog entry found for ${name}@${version}\n` : `- ${name}@${version} is a pre-release; no changelog required\n`);
  } else if (command === "context") {
    const versionIndex = rest.indexOf("--version");
    const version = versionIndex === -1 ? undefined : rest[versionIndex + 1];
    process.stdout.write(`${JSON.stringify(context(name, version), null, 2)}\n`);
  } else {
    throw new Error("Usage: node scripts/changelog.mjs <check|context> <skill> [--version X.Y.Z]");
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
