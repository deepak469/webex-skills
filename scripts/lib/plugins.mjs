import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { isAbsolute, join, relative, resolve, sep } from "node:path";

export const MARKETPLACE_NAME = "webex-skills";

export const SURFACES = [
  {
    name: "Codex",
    manifest: ".codex-plugin/plugin.json",
    marketplace: ".agents/plugins/marketplace.json",
    sourceType: "codex",
  },
  {
    name: "Claude Code",
    manifest: ".claude-plugin/plugin.json",
    marketplace: ".claude-plugin/marketplace.json",
    sourceType: "path",
  },
  {
    name: "Cursor",
    manifest: ".cursor-plugin/plugin.json",
    marketplace: ".cursor-plugin/marketplace.json",
    sourceType: "path",
  },
  {
    name: "Windsurf",
    manifest: ".windsurf-plugin/plugin.json",
    marketplace: ".windsurf-plugin/marketplace.json",
    sourceType: "path",
  },
];

const VERSION_RE = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;

function repoPath(root, path) {
  return relative(root, path).split(sep).join("/");
}

function isWithin(parent, target) {
  const path = relative(parent, target);
  return path === "" || (path !== ".." && !path.startsWith(`..${sep}`) && !isAbsolute(path));
}

function readJson(root, path, errors, required = false) {
  if (!existsSync(path)) {
    if (required) errors.push(`${repoPath(root, path)} is missing`);
    return null;
  }
  try {
    const value = JSON.parse(readFileSync(path, "utf8"));
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      errors.push(`${repoPath(root, path)} must contain a JSON object`);
      return null;
    }
    return value;
  } catch (error) {
    errors.push(`${repoPath(root, path)} is not valid JSON: ${error.message}`);
    return null;
  }
}

function frontmatterFields(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;

  const lines = match[1].split(/\r?\n/);
  const fields = {};
  for (let index = 0; index < lines.length; index += 1) {
    const field = lines[index].match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!field) continue;

    const [, key, rawValue] = field;
    if ([">", ">-", ">+", "|", "|-", "|+"].includes(rawValue.trim())) {
      const parts = [];
      while (index + 1 < lines.length && /^\s+\S/.test(lines[index + 1])) {
        parts.push(lines[++index].trim());
      }
      fields[key] = parts.join(" ").trim();
    } else {
      fields[key] = rawValue.trim().replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, "$1$2");
    }
  }
  return fields;
}

function checkComponentPath(root, pluginRoot, manifest, key, label, errors) {
  const value = manifest[key];
  if (value === undefined) return [];
  const values = Array.isArray(value) ? value : [value];
  const paths = [];
  for (const item of values) {
    if (typeof item !== "string" || !item.startsWith("./")) {
      errors.push(`${label} ${key} must use a relative path beginning with ./`);
      continue;
    }
    const target = resolve(pluginRoot, item);
    if (!isWithin(pluginRoot, target) || !existsSync(target)) {
      errors.push(`${label} ${key} points to a missing or out-of-package path: ${item}`);
      continue;
    }
    paths.push(target);
  }
  return paths;
}

function checkAsset(root, pluginRoot, value, label, errors) {
  if (value === undefined) return;
  if (typeof value !== "string" || !value.startsWith("./")) {
    errors.push(`${label} must use a relative path beginning with ./`);
    return;
  }
  const target = resolve(pluginRoot, value);
  if (!isWithin(pluginRoot, target) || !existsSync(target) || !statSync(target).isFile()) {
    errors.push(`${label} points to a missing or out-of-package file: ${value}`);
  }
}

function findSkills(root, pluginRoot, skillRoots, pluginName, errors) {
  const skills = new Map();
  for (const skillRoot of skillRoots) {
    if (!statSync(skillRoot).isDirectory()) {
      errors.push(`${repoPath(root, skillRoot)} must be a directory`);
      continue;
    }
    for (const entry of readdirSync(skillRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const skillPath = join(skillRoot, entry.name, "SKILL.md");
      if (!existsSync(skillPath)) {
        errors.push(`${repoPath(root, skillPath)} is missing`);
        continue;
      }
      const fields = frontmatterFields(readFileSync(skillPath, "utf8"));
      if (!fields) {
        errors.push(`${repoPath(root, skillPath)} is missing YAML frontmatter`);
        continue;
      }
      if (fields.name !== entry.name) {
        errors.push(`${repoPath(root, skillPath)} name must match its folder (${entry.name})`);
      }
      if (!fields.description) errors.push(`${repoPath(root, skillPath)} is missing a description`);
      skills.set(entry.name, {
        name: entry.name,
        description: fields.description || "",
        path: repoPath(root, join(skillRoot, entry.name)),
      });
    }
  }
  if (skills.size === 0) errors.push(`plugins/${pluginName} must include at least one skill with SKILL.md`);
  return [...skills.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function hasForbiddenEnvironmentFile(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name === ".DS_Store" || entry.name === "__pycache__") continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      if (hasForbiddenEnvironmentFile(path)) return true;
    } else if (entry.name === ".env" || (entry.name.startsWith(".env.") && entry.name !== ".env.example")) {
      return true;
    }
  }
  return false;
}

function validatePlugin(root, pluginRoot, errors) {
  const pluginName = pluginRoot.split(sep).at(-1);
  const manifests = new Map();
  for (const surface of SURFACES) {
    const manifestPath = join(pluginRoot, surface.manifest);
    if (!existsSync(manifestPath)) continue;
    const manifest = readJson(root, manifestPath, errors, true);
    if (!manifest) continue;
    manifests.set(surface.name, { manifest, surface, path: manifestPath });
    if (manifest.name !== pluginName) {
      errors.push(`${repoPath(root, manifestPath)} name must match its plugin folder (${pluginName})`);
    }
    if (typeof manifest.description !== "string" || !manifest.description.trim()) {
      errors.push(`${repoPath(root, manifestPath)} description is required`);
    }
    if (typeof manifest.version !== "string" || !VERSION_RE.test(manifest.version)) {
      errors.push(`${repoPath(root, manifestPath)} version must be semantic versioning`);
    }
    if (manifest.skills === undefined) {
      errors.push(`${repoPath(root, manifestPath)} must declare a skills path`);
    }
    for (const component of ["commands", "rules"]) {
      checkComponentPath(root, pluginRoot, manifest, component, repoPath(root, manifestPath), errors);
    }
    checkAsset(root, pluginRoot, manifest.logo, `${repoPath(root, manifestPath)} logo`, errors);
    checkAsset(root, pluginRoot, manifest.interface?.logo, `${repoPath(root, manifestPath)} interface.logo`, errors);
    checkAsset(root, pluginRoot, manifest.interface?.composerIcon, `${repoPath(root, manifestPath)} interface.composerIcon`, errors);
  }

  if (manifests.size === 0) {
    errors.push(`plugins/${pluginName} has no supported plugin manifest`);
    return null;
  }
  const versions = new Set([...manifests.values()].map(({ manifest }) => manifest.version));
  if (versions.size !== 1 || versions.has(undefined)) {
    errors.push(`plugins/${pluginName} has mismatched versions across its plugin manifests`);
  }

  const skillRoots = new Set();
  for (const { manifest, path } of manifests.values()) {
    const paths = checkComponentPath(root, pluginRoot, manifest, "skills", repoPath(root, path), errors);
    paths.forEach((skillRoot) => skillRoots.add(skillRoot));
  }
  const skills = findSkills(root, pluginRoot, [...skillRoots], pluginName, errors);
  if (hasForbiddenEnvironmentFile(pluginRoot)) {
    errors.push(`plugins/${pluginName} contains a secret environment file; only .env.example is allowed`);
  }

  const preferred = manifests.get("Codex") || manifests.values().next().value;
  const manifest = preferred.manifest;
  return {
    name: pluginName,
    displayName: manifest.interface?.displayName || manifest.displayName || pluginName,
    version: manifest.version,
    description: manifest.description,
    surfaces: [...manifests.keys()].sort(),
    skills,
    manifests,
  };
}

function validateMarketplace(root, surface, plugins, errors) {
  const path = join(root, surface.marketplace);
  if (!existsSync(path)) {
    if (plugins.some((plugin) => plugin.manifests.has(surface.name))) {
      errors.push(`${surface.marketplace} is required for plugins that support ${surface.name}`);
    }
    return;
  }
  const marketplace = readJson(root, path, errors, true);
  if (!marketplace) return;
  if (marketplace.name !== MARKETPLACE_NAME) {
    errors.push(`${surface.marketplace} name must be ${MARKETPLACE_NAME}`);
  }
  if (!Array.isArray(marketplace.plugins)) {
    errors.push(`${surface.marketplace} plugins must be an array`);
    return;
  }

  const entries = new Map();
  for (const entry of marketplace.plugins) {
    if (!entry || typeof entry.name !== "string" || !entry.name) {
      errors.push(`${surface.marketplace} contains a plugin entry without a name`);
      continue;
    }
    if (entries.has(entry.name)) errors.push(`${surface.marketplace} contains duplicate entry ${entry.name}`);
    entries.set(entry.name, entry);
    const plugin = plugins.find((item) => item.name === entry.name);
    if (!plugin || !plugin.manifests.has(surface.name)) {
      errors.push(`${surface.marketplace} lists ${entry.name}, but its ${surface.name} manifest is missing`);
      continue;
    }
    const expectedPath = `./plugins/${entry.name}`;
    if (surface.sourceType === "codex") {
      if (entry.source?.source !== "local" || entry.source?.path !== expectedPath) {
        errors.push(`${surface.marketplace} entry ${entry.name} source must be local at ${expectedPath}`);
      }
    } else if (entry.source !== expectedPath) {
      errors.push(`${surface.marketplace} entry ${entry.name} source must be ${expectedPath}`);
    }
    const version = plugin.manifests.get(surface.name).manifest.version;
    if (entry.version !== version) errors.push(`${surface.marketplace} entry ${entry.name} version must match ${version}`);
  }

  for (const plugin of plugins) {
    if (plugin.manifests.has(surface.name) && !entries.has(plugin.name)) {
      errors.push(`${surface.marketplace} is missing ${plugin.name}`);
    }
  }
}

export function inspectPlugins(root) {
  const errors = [];
  const pluginsRoot = join(root, "plugins");
  if (!existsSync(pluginsRoot) || !statSync(pluginsRoot).isDirectory()) {
    return { plugins: [], errors: ["plugins/ directory is missing"] };
  }
  const directories = readdirSync(pluginsRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory());
  if (directories.length === 0) errors.push("plugins/ must contain at least one plugin directory");

  const plugins = [];
  for (const entry of directories) {
    const pluginRoot = join(pluginsRoot, entry.name);
    const plugin = validatePlugin(root, pluginRoot, errors);
    if (plugin) plugins.push(plugin);
  }
  for (const surface of SURFACES) validateMarketplace(root, surface, plugins, errors);
  plugins.sort((a, b) => a.name.localeCompare(b.name));
  return { plugins, errors };
}

export function renderCatalog(plugins) {
  const catalog = {
    name: MARKETPLACE_NAME,
    plugins: plugins.map(({ name, displayName, version, description, surfaces, skills }) => ({
      name,
      displayName,
      version,
      description,
      surfaces,
      skills: skills.map(({ name: skillName, description: skillDescription, path }) => ({
        name: skillName,
        description: skillDescription,
        path,
      })),
    })),
  };
  const markdown = [
    `# ${MARKETPLACE_NAME}`,
    "",
    "Available plugin bundles and their skills. Generated from plugin manifests and `SKILL.md` frontmatter; edit the source files and run `npm run catalog:generate`.",
    "",
  ];
  for (const plugin of catalog.plugins) {
    markdown.push(`## ${plugin.displayName} (${plugin.version})`, "", plugin.description, "", `Surfaces: ${plugin.surfaces.join(", ")}`, "", "| Skill | Description |", "| --- | --- |");
    for (const skill of plugin.skills) {
      const description = skill.description.replaceAll("|", "\\|").replaceAll("\n", " ");
      markdown.push(`| [\`${skill.name}\`](<${skill.path}/SKILL.md>) | ${description} |`);
    }
    markdown.push("");
  }
  return { json: `${JSON.stringify(catalog, null, 2)}\n`, markdown: `${markdown.join("\n").trimEnd()}\n` };
}
