#!/usr/bin/env node
// Require a plugin version bump when its bundle inputs change in a pull request.

import { execFileSync } from "node:child_process";
import { pluginsMissingVersionBumps } from "./lib/plugin-versions.mjs";

const [base, head] = process.argv.slice(2);
const ZERO_SHA = /^0+$/;

if (!base || !head || ZERO_SHA.test(base)) {
  process.stdout.write("- No previous commit available; skipping plugin version comparison\n");
  process.exit(0);
}

function git(...args) {
  return execFileSync("git", args, { encoding: "utf8", maxBuffer: 16 * 1024 * 1024 }).trim();
}

function pluginsAt(revision) {
  const paths = git("ls-tree", "-r", "--name-only", revision, "--", "plugins")
    .split("\n")
    .filter((path) => /^plugins\/[^/]+\/plugin\.json$/.test(path));
  return paths.map((path) => JSON.parse(git("show", `${revision}:${path}`)));
}

try {
  const changedPaths = git("diff", "--name-only", base, head).split("\n").filter(Boolean);
  const errors = pluginsMissingVersionBumps(changedPaths, pluginsAt(base), pluginsAt(head));
  if (errors.length) {
    process.stderr.write(`✗ plugin version policy\n${errors.map((error) => `  - ${error}`).join("\n")}\n`);
    process.exitCode = 1;
  } else {
    process.stdout.write("✓ plugin versions updated for changed bundle inputs\n");
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
