#!/usr/bin/env node
// Usage: node scripts/validate-skill.mjs [skill-name ...]   (no args = all skills)

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { REPO_ROOT, listSkills, readPackage, skillDirectory } from "./lib/skills.mjs";

const SEMVER = /^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/;
const PUBLISH_WORKFLOW = join(REPO_ROOT, ".github", "workflows", "publish.yml");

function parseFrontmatter(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const fields = {};
  for (const line of match[1].split(/\r?\n/)) {
    const pair = line.match(/^([A-Za-z_-]+):\s*(.*)$/);
    if (pair) fields[pair[1]] = pair[2].trim();
  }
  return fields;
}

export function validateSkill(name) {
  const errors = [];
  const directory = skillDirectory(name);
  const shippedDirectory = join(directory, "skill", name);

  for (const required of ["README.md", "package.json", join("skill", name, "SKILL.md"), join("release", "CHANGELOG.md")]) {
    if (!existsSync(join(directory, required))) errors.push(`missing ${required}`);
  }
  if (errors.length) return errors;

  const pkg = readPackage(name);
  // Keeps `release/<name>-latest.tgz` and the `npx ... <name> install` command derivable from the skill name.
  if (pkg.name !== name) errors.push(`package.json: name "${pkg.name}" must equal folder "${name}"`);
  const binNames = Object.keys(pkg.bin || {});
  if (binNames.length !== 1 || binNames[0] !== name) {
    errors.push(`package.json: "bin" must define exactly one command named "${name}"`);
  }
  if (!SEMVER.test(pkg.version || "")) errors.push(`package.json: invalid version "${pkg.version}"`);
  if (!Array.isArray(pkg.files) || !pkg.files.includes(`skill/${name}/`)) {
    errors.push(`package.json: "files" must include "skill/${name}/"`);
  }
  if (pkg.files?.some((entry) => entry.startsWith("release"))) {
    errors.push('package.json: "files" must not include release/');
  }
  for (const script of ["test", "pack:check"]) {
    if (!pkg.scripts?.[script]) errors.push(`package.json: missing "${script}" script`);
  }
  for (const binPath of Object.values(pkg.bin || {})) {
    if (!existsSync(join(directory, binPath))) errors.push(`package.json: bin target missing: ${binPath}`);
  }

  const frontmatter = parseFrontmatter(readFileSync(join(shippedDirectory, "SKILL.md"), "utf8"));
  if (!frontmatter) {
    errors.push("SKILL.md: missing YAML frontmatter");
  } else {
    if (frontmatter.name !== name) errors.push(`SKILL.md: name "${frontmatter.name}" must equal folder "${name}"`);
    if (!frontmatter.description) errors.push("SKILL.md: missing description");
    else if (frontmatter.description.length > 1024) errors.push("SKILL.md: description exceeds 1024 characters");
  }

  const workflow = existsSync(PUBLISH_WORKFLOW) ? readFileSync(PUBLISH_WORKFLOW, "utf8") : "";
  if (!new RegExp(`^\\s*-\\s*${name}\\s*$`, "m").test(workflow)) {
    errors.push(`.github/workflows/publish.yml: add "${name}" to the skill input options`);
  }
  return errors;
}

const names = process.argv.slice(2).length ? process.argv.slice(2) : listSkills();
let failed = false;
for (const name of names) {
  const errors = validateSkill(name);
  if (errors.length) {
    failed = true;
    process.stderr.write(`✗ ${name}\n${errors.map((error) => `  - ${error}`).join("\n")}\n`);
  } else {
    process.stdout.write(`✓ ${name}\n`);
  }
}
process.exitCode = failed ? 1 : 0;
