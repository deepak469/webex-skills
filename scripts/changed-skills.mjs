#!/usr/bin/env node
// Usage: node scripts/changed-skills.mjs <base-ref> [head-ref]
// Prints a JSON array of skills affected by the diff; shared files affect all skills.

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { REPO_ROOT, SKILLS_ROOT, listSkills } from "./lib/skills.mjs";

const SHARED_PATHS = [
  /^scripts\/(?:lib\/skills\.mjs|validate-skill\.mjs|changed-skills\.mjs|package-skill\.mjs|changelog\.mjs)$/,
  /^scripts\/lib\/changelog\.mjs$/,
  /^\.github\/workflows\/publish\.yml$/,
  /^package\.json$/,
];

function git(...args) {
  return execFileSync("git", args, { cwd: REPO_ROOT, encoding: "utf8" }).trim();
}

function commitExists(ref) {
  if (!ref || /^0+$/.test(ref)) return false;
  try {
    git("cat-file", "-e", `${ref}^{commit}`);
    return true;
  } catch {
    return false;
  }
}

export function changedSkills(base, head = "HEAD") {
  if (!commitExists(base)) return listSkills();
  const files = git("diff", "--name-only", `${base}...${head}`).split("\n").filter(Boolean);
  if (files.some((file) => SHARED_PATHS.some((pattern) => pattern.test(file)))) return listSkills();
  const skills = new Set();
  for (const file of files) {
    const match = file.match(/^skills\/([^/]+)\//);
    if (match && existsSync(join(SKILLS_ROOT, match[1]))) skills.add(match[1]);
  }
  return [...skills].sort();
}

process.stdout.write(`${JSON.stringify(changedSkills(process.argv[2], process.argv[3]))}\n`);
