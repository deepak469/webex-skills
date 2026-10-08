#!/usr/bin/env node

import { access, cp, mkdir } from "node:fs/promises";
import { realpathSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SKILL_NAME = "webex-api-knowledge";
const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const SKILL_DIRECTORY = resolve(SCRIPT_DIRECTORY, "..", "skill", SKILL_NAME);
const CLIENTS = new Set(["codex", "copilot", "claude", "all"]);
const SCOPES = new Set(["project", "user"]);

function usage() {
  return [
    "Usage: webex-api-knowledge-skill install",
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
  process.stdout.write(`${JSON.stringify({ skill: SKILL_NAME, results }, null, 2)}\n`);
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
