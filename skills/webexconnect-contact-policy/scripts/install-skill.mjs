#!/usr/bin/env node

import { access, cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const PACKAGE_DIRECTORY = resolve(SCRIPT_DIRECTORY, "..");
const { name: SKILL_NAME } = JSON.parse(readFileSync(resolve(PACKAGE_DIRECTORY, "package.json"), "utf8"));
const SKILL_DIRECTORY = resolve(PACKAGE_DIRECTORY, "skill", SKILL_NAME);
const { version: VERSION } = JSON.parse(readFileSync(resolve(PACKAGE_DIRECTORY, "package.json"), "utf8"));
const CLIENTS = new Set(["codex", "copilot", "claude", "all"]);
const SCOPES = new Set(["project", "user"]);

function usage() {
  return [
    `Usage: ${SKILL_NAME} install`,
    "       --client <codex|copilot|claude|all>",
    "       --scope <project|user> [--force]",
    "",
    "Project scope installs relative to the current working directory.",
  ].join("\n");
}

export function parseArguments(argv) {
  const args = [...argv];
  if (args[0] === "install") args.shift();
  if (args.includes("--help") || args.includes("-h")) {
    return { help: true };
  }
  let client = null;
  let scope = null;
  let force = false;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--client") {
      client = args[index + 1] || null;
      index += 1;
    } else if (argument === "--scope") {
      scope = args[index + 1] || null;
      index += 1;
    } else if (argument === "--force") {
      force = true;
    } else {
      throw new Error(usage());
    }
  }
  if (!CLIENTS.has(client) || !SCOPES.has(scope)) {
    throw new Error(usage());
  }
  return { client, scope, force, help: false };
}

export function installationTargets(client, scope, cwd = process.cwd()) {
  const clients = client === "all" ? ["codex", "copilot", "claude"] : [client];
  const targets = clients.map((selectedClient) => {
    if (scope === "project") {
      if (selectedClient === "claude") {
        return join(cwd, ".claude", "skills", SKILL_NAME);
      }
      return join(cwd, ".agents", "skills", SKILL_NAME);
    }
    if (selectedClient === "codex") {
      return join(homedir(), ".agents", "skills", SKILL_NAME);
    }
    if (selectedClient === "copilot") {
      return join(homedir(), ".copilot", "skills", SKILL_NAME);
    }
    return join(homedir(), ".claude", "skills", SKILL_NAME);
  });
  return [...new Set(targets.map((target) => resolve(target)))];
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

// Sets `metadata.version` in SKILL.md frontmatter, replacing any existing value.
export function stampVersion(markdown, version) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---/.exec(markdown);
  if (!match) throw new Error("SKILL.md is missing YAML frontmatter");
  const lines = match[1].split(/\r?\n/);
  const versionLine = `  version: ${JSON.stringify(version)}`;
  const metadataIndex = lines.findIndex((line) => /^metadata:\s*$/.test(line));
  if (metadataIndex === -1) {
    lines.push("metadata:", versionLine);
  } else {
    let end = metadataIndex + 1;
    while (end < lines.length && /^\s+\S/.test(lines[end])) end += 1;
    const block = lines
      .slice(metadataIndex + 1, end)
      .filter((line) => !/^\s+version:/.test(line));
    lines.splice(metadataIndex + 1, end - metadataIndex - 1, versionLine, ...block);
  }
  return `---\n${lines.join("\n")}\n---${markdown.slice(match[0].length)}`;
}

export async function install({ client, scope, force = false }) {
  const results = [];
  for (const target of installationTargets(client, scope)) {
    if (target === SKILL_DIRECTORY) {
      results.push({ target, status: "already-installed" });
      continue;
    }
    if (await pathExists(target) && !force) {
      throw new Error(
        `Skill already exists at ${target}; inspect it and rerun with --force to update it`,
      );
    }
    await mkdir(dirname(target), { recursive: true });
    await cp(SKILL_DIRECTORY, target, {
      recursive: true,
      force,
      errorOnExist: !force,
    });
    const skillFile = join(target, "SKILL.md");
    await writeFile(skillFile, stampVersion(await readFile(skillFile, "utf8"), VERSION));
    results.push({ target, status: "installed" });
  }
  return results;
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(`${usage()}\n`);
    return;
  }
  const results = await install(options);
  process.stdout.write(`${JSON.stringify({ skill: SKILL_NAME, version: VERSION, results }, null, 2)}\n`);
}

const invokedPath = process.argv[1]
  ? realpathSync(resolve(process.argv[1]))
  : null;
if (invokedPath === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
