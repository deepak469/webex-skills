import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { inspectPlugins, renderCatalog } from "../scripts/lib/plugins.mjs";
import { pluginsMissingVersionBumps } from "../scripts/lib/plugin-versions.mjs";

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), "webex-skills-plugins-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  return root;
}

function addPlugin(root, name, skills, surfaces = ["codex"], version = "1.0.0") {
  const manifests = { codex: ".codex-plugin/plugin.json", cursor: ".cursor-plugin/plugin.json" };
  const pluginRoot = join(root, "plugins", name);
  mkdirSync(pluginRoot, { recursive: true });
  writeFileSync(join(pluginRoot, "plugin.json"), `${JSON.stringify({ name, version, displayName: name, description: `${name} plugin description`, skills }, null, 2)}\n`);
  for (const surface of surfaces) {
    const relativeManifest = manifests[surface];
    const manifestPath = join(pluginRoot, relativeManifest);
    mkdirSync(dirname(manifestPath), { recursive: true });
    const manifest = { name, version, description: `${name} plugin description`, skills: "./skills/" };
    if (surface === "codex") manifest.interface = { displayName: name };
    if (surface === "cursor") manifest.displayName = name;
    writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  }
  for (const skill of skills) {
    const directory = join(root, "skills", skill);
    mkdirSync(join(directory, "skill", skill), { recursive: true });
    writeFileSync(join(directory, "package.json"), JSON.stringify({ name: skill, version: "1.0.0" }));
    writeFileSync(join(directory, "skill", skill, "SKILL.md"), `---\nname: ${skill}\ndescription: >\n  Guidance for ${skill}.\n---\n`);
  }
}

function writeMarketplace(root, surface, pluginNames) {
  const marketplacePaths = { codex: ".agents/plugins/marketplace.json", cursor: ".cursor-plugin/marketplace.json" };
  const marketplacePath = join(root, marketplacePaths[surface]);
  mkdirSync(dirname(marketplacePath), { recursive: true });
  const plugins = pluginNames.map((name) => ({
    name,
    version: "1.0.0",
    source: surface === "codex"
      ? { source: "local", path: `./plugin-packages/${name}` }
      : `./plugin-packages/${name}`,
  }));
  writeFileSync(marketplacePath, `${JSON.stringify({ name: "webex-skills", plugins }, null, 2)}\n`);
}

test("discovers plugin skill links and catalogs standalone skill package paths", (t) => {
  const root = fixture(t);
  addPlugin(root, "alpha", ["alpha-one"], ["codex", "cursor"]);
  addPlugin(root, "beta", ["beta-one", "beta-two"]);
  writeMarketplace(root, "codex", ["alpha", "beta"]);
  writeMarketplace(root, "cursor", ["alpha"]);

  const result = inspectPlugins(root);
  assert.deepEqual(result.errors, []);
  assert.equal(result.plugins.length, 2);
  assert.equal(result.plugins.find((plugin) => plugin.name === "beta").skills.length, 2);
  const catalog = renderCatalog(result.plugins);
  assert.match(catalog.json, /"name": "beta-two"/);
  assert.match(catalog.markdown, /\[`beta-two`\]/);
  assert.match(catalog.json, /skills\/beta-two\/skill\/beta-two/);
});

test("reports duplicate or unresolved skill package links", (t) => {
  const root = fixture(t);
  addPlugin(root, "alpha", ["alpha-one"]);
  const recipePath = join(root, "plugins", "alpha", "plugin.json");
  const recipe = JSON.parse(readFileSync(recipePath, "utf8"));
  recipe.skills = ["alpha-one", "missing-skill", "alpha-one"];
  writeFileSync(recipePath, `${JSON.stringify(recipe)}\n`);
  writeMarketplace(root, "codex", ["alpha"]);

  const result = inspectPlugins(root);
  assert.ok(result.errors.some((error) => error.includes("missing-skill")));
  assert.ok(result.errors.some((error) => error.includes("duplicate skill link alpha-one")));
});

test("reports version drift between a plugin recipe and its platform manifest", (t) => {
  const root = fixture(t);
  addPlugin(root, "alpha", ["alpha-one"], ["codex", "cursor"]);
  const cursorManifest = join(root, "plugins", "alpha", ".cursor-plugin", "plugin.json");
  const manifest = JSON.parse(readFileSync(cursorManifest, "utf8"));
  manifest.version = "2.0.0";
  writeFileSync(cursorManifest, `${JSON.stringify(manifest)}\n`);
  writeMarketplace(root, "codex", ["alpha"]);
  writeMarketplace(root, "cursor", ["alpha"]);

  const result = inspectPlugins(root);
  assert.ok(result.errors.some((error) => error.includes("version must match plugin.json")));
});

test("requires a plugin version bump when linked skill content changes", () => {
  const previous = [{ name: "alpha", version: "1.0.0", skills: ["alpha-one"] }];
  const unchanged = [{ name: "alpha", version: "1.0.0", skills: ["alpha-one"] }];
  assert.equal(pluginsMissingVersionBumps(["skills/alpha-one/skill/alpha-one/SKILL.md"], previous, unchanged).length, 1);
  assert.equal(pluginsMissingVersionBumps(["plugins/alpha/commands/send.md"], previous, unchanged).length, 1);
  const bumped = [{ ...unchanged[0], version: "1.0.1" }];
  assert.deepEqual(pluginsMissingVersionBumps(["skills/alpha-one/package.json"], previous, bumped), []);
  assert.deepEqual(pluginsMissingVersionBumps(["skills/unlinked/skill/unlinked/SKILL.md"], previous, unchanged), []);
  assert.deepEqual(pluginsMissingVersionBumps(["plugins/alpha/release/CHANGELOG.md"], previous, unchanged), []);
});

test("standalone Webex Connect installs use private GitHub release packages", () => {
  const root = new URL("../", import.meta.url).pathname;
  const skillsRoot = join(root, "skills");
  const connectSkills = readdirSync(skillsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name !== "webex-api-knowledge");
  assert.equal(connectSkills.length, 19);
  for (const entry of connectSkills) {
    const directory = join(skillsRoot, entry.name);
    const pkg = JSON.parse(readFileSync(join(directory, "package.json"), "utf8"));
    const readme = readFileSync(join(directory, "README.md"), "utf8");
    const archive = join(directory, "release", `${pkg.name}-latest.tgz`);
    assert.equal(pkg.private, true, `${pkg.name} must not publish to npm`);
    assert.ok(readme.includes(`https://raw.githubusercontent.com/webex/webex-skills/main/skills/${pkg.name}/release/${pkg.name}-latest.tgz`), `${pkg.name} README must install from its repository release package`);
    assert.ok(readme.includes("npx --yes"), `${pkg.name} README must use noninteractive npm execution`);
    assert.ok(existsSync(archive), `${pkg.name} latest release archive is missing`);
  }
});

test("source plugin contains no skills and build assembles all linked skills", () => {
  const root = new URL("../", import.meta.url).pathname;
  const source = join(root, "plugins", "webex-connect-ai");
  const recipe = JSON.parse(readFileSync(join(source, "plugin.json"), "utf8"));
  assert.equal(recipe.skills.length, 19);
  assert.ok(!readdirSync(source).includes("skills"));
  assert.ok(!readdirSync(source, { recursive: true }).some((path) => path.endsWith("SKILL.md")));

  execFileSync(process.execPath, [join(root, "scripts", "build-plugins.mjs")], { cwd: root, stdio: "pipe" });
  const built = join(root, "plugin-packages", "webex-connect-ai");
  const skillFiles = readdirSync(join(built, "skills"), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => join(built, "skills", entry.name, "SKILL.md"));
  assert.equal(skillFiles.length, 19);
  assert.ok(skillFiles.every((path) => existsSync(path)));
  const lock = JSON.parse(readFileSync(join(built, "plugin-lock.json"), "utf8"));
  assert.equal(lock.version, recipe.version);
  assert.equal(Object.keys(lock.skills).length, 19);
  assert.ok(Object.values(lock.skills).every((version) => /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)));
  assert.ok(!readdirSync(built).includes("release"));
});
