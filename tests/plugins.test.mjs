import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { inspectPlugins, renderCatalog } from "../scripts/lib/plugins.mjs";

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), "webex-skills-plugins-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  return root;
}

function addPlugin(root, name, skills, surfaces = ["codex"], version = "1.0.0") {
  const manifests = {
    codex: ".codex-plugin/plugin.json",
    cursor: ".cursor-plugin/plugin.json",
  };
  for (const surface of surfaces) {
    const relativeManifest = manifests[surface];
    const manifestPath = join(root, "plugins", name, relativeManifest);
    mkdirSync(dirname(manifestPath), { recursive: true });
    const manifest = {
      name,
      version,
      description: `${name} plugin description`,
      skills: "./skills/",
    };
    if (surface === "codex") manifest.interface = { displayName: name };
    if (surface === "cursor") manifest.displayName = name;
    writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  }
  for (const skill of skills) {
    const directory = join(root, "plugins", name, "skills", skill);
    mkdirSync(directory, { recursive: true });
    writeFileSync(join(directory, "SKILL.md"), `---\nname: ${skill}\ndescription: >\n  Guidance for ${skill}.\n---\n`);
  }
}

function writeMarketplace(root, surface, pluginNames) {
  const marketplacePaths = {
    codex: ".agents/plugins/marketplace.json",
    cursor: ".cursor-plugin/marketplace.json",
  };
  const marketplacePath = join(root, marketplacePaths[surface]);
  mkdirSync(dirname(marketplacePath), { recursive: true });
  const plugins = pluginNames.map((name) => ({
    name,
    version: "1.0.0",
    source: surface === "codex"
      ? { source: "local", path: `./plugins/${name}` }
      : `./plugins/${name}`,
  }));
  writeFileSync(marketplacePath, `${JSON.stringify({ name: "webex-skills", plugins }, null, 2)}\n`);
}

test("discovers multiple plugins and catalogues each plugin's own skill count", (t) => {
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
  assert.match(catalog.json, /"name": "beta"/);
  assert.match(catalog.markdown, /\[`beta-two`\]/);
});

test("reports version drift between platform manifests", (t) => {
  const root = fixture(t);
  addPlugin(root, "alpha", ["alpha-one"], ["codex", "cursor"]);
  const cursorManifest = join(root, "plugins", "alpha", ".cursor-plugin", "plugin.json");
  const manifest = JSON.parse(readFileSync(cursorManifest, "utf8"));
  manifest.version = "2.0.0";
  writeFileSync(cursorManifest, `${JSON.stringify(manifest)}\n`);
  writeMarketplace(root, "codex", ["alpha"]);
  writeMarketplace(root, "cursor", ["alpha"]);

  const result = inspectPlugins(root);
  assert.ok(result.errors.some((error) => error.includes("mismatched versions")));
  assert.ok(result.errors.some((error) => error.includes("version must match 2.0.0")));
});
