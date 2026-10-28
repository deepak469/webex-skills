const bundledSkillPath = /^skills\/([^/]+)\/(?:package\.json|skill\/\1(?:\/|$))/;

export function pluginsMissingVersionBumps(changedPaths, previousPlugins, currentPlugins) {
  const previousByName = new Map(previousPlugins.map((plugin) => [plugin.name, plugin]));
  const changedSkills = new Set(
    changedPaths.map((path) => path.match(bundledSkillPath)?.[1]).filter(Boolean),
  );
  const errors = [];

  for (const plugin of currentPlugins) {
    const previous = previousByName.get(plugin.name);
    if (!previous) continue;

    const sourceChanged = changedPaths.some((path) =>
      path.startsWith(`plugins/${plugin.name}/`) && !path.startsWith(`plugins/${plugin.name}/release/`),
    );
    const linkedSkillChanged = [...new Set([...previous.skills, ...plugin.skills])]
      .some((name) => changedSkills.has(name));

    if ((sourceChanged || linkedSkillChanged) && previous.version === plugin.version) {
      errors.push(`${plugin.name} bundles changed content but remains at ${plugin.version}; bump plugins/${plugin.name}/plugin.json and synchronize its manifests and marketplace entries`);
    }
  }

  return errors;
}
