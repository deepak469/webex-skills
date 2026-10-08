import { readdirSync, existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const SKILLS_ROOT = join(REPO_ROOT, "skills");
const SKILL_NAME_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*$/;

export function listSkills() {
  return readdirSync(SKILLS_ROOT, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && SKILL_NAME_PATTERN.test(entry.name))
    .map((entry) => entry.name)
    .sort();
}

export function skillDirectory(name) {
  if (!SKILL_NAME_PATTERN.test(name || "") || !existsSync(join(SKILLS_ROOT, name))) {
    throw new Error(`Unknown skill: ${name}. Available: ${listSkills().join(", ")}`);
  }
  return join(SKILLS_ROOT, name);
}

export function readPackage(name) {
  return JSON.parse(readFileSync(join(skillDirectory(name), "package.json"), "utf8"));
}
