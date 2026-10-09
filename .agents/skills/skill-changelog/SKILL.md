---
name: skill-changelog
description: Prepare the changelog for a stable release of a skill in this webex-skills repository. Collects commits since the last stable tag, drafts a CHANGELOG.md entry for user review, bumps the skill version if needed, pushes a changelog branch, and opens a pull request. Use when releasing a stable skill version or when the "Package skill release" workflow fails for a missing changelog entry.
---

# Skill changelog

Prepares `skills/<skill>/release/CHANGELOG.md` for a stable version (`X.Y.Z`) and opens a PR. Pre-release versions (`X.Y.Z-beta.N`) never get changelog entries. Run all commands from the repository root.

## 1. Choose skill and version

- Skill: the folder name under `skills/`. If the user did not say which, list the folders and ask.
- Version: must be stable `X.Y.Z`. If the user did not give one, read `version` in `skills/<skill>/package.json`: a pre-release `X.Y.Z-beta.N` suggests `X.Y.Z`; an already-released stable version needs a bump. Suggest a semver bump from the changes (breaking → major, feature → minor, fix only → patch) and confirm with the user.

## 2. Prepare the branch

1. Require a clean working tree (`git status --porcelain`). If it is not clean, stop and ask the user; never stash, reset, or discard their changes.
2. `git fetch origin --tags`
3. `git switch -c changelog/<skill>-<version> origin/main`

## 3. Collect changes

```sh
node scripts/changelog.mjs context <skill> --version <version>
```

The JSON contains the previous stable tag, the commit range, `commits` (subject and body), and changed `files`. Release artifacts are already excluded. If `entryExists` is true, show the existing entry and ask whether to revise it. If `tagsFound` is 0, this is the first stable release; the range is the skill's full history, so draft an initial-release summary from the skill's README and files rather than from commit subjects.

When commit messages are vague, inspect the actual diff before writing: `git diff <previousTag> HEAD -- skills/<skill> ':(exclude)skills/<skill>/release'` (use the empty range only when there is no previous tag).

## 4. Draft the entry

Format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Breaking
- ...

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Security
- ...
```

- Use today's date. Omit empty sections; keep this section order.
- Write for skill users: what changed for them, not how. One line per change, present tense, no commit hashes.
- Merge related commits into one bullet. Drop changes with no user impact (CI, tests, refactors, typos) unless they are the only changes.
- Only describe changes evidenced by commits or diffs; never invent features.
- Never include secrets, tokens, internal hostnames, or personal data.

Show the draft to the user and apply their edits. Do not continue until they confirm it.

## 5. Write, validate, and open the PR

1. Insert the entry in `skills/<skill>/release/CHANGELOG.md` directly above the most recent existing `## [` entry (or at the end of the file if there is none). Keep the file header.
2. If `versionBumpNeeded` is true, change only the `version` field in `skills/<skill>/package.json`.
3. Validate:

   ```sh
   node scripts/changelog.mjs check <skill>
   node scripts/validate-skill.mjs <skill>
   npm test --workspace skills/<skill>
   ```

4. Commit only the changelog and `package.json`:

   ```sh
   git add skills/<skill>/release/CHANGELOG.md skills/<skill>/package.json
   git commit -m "docs(<skill>): changelog for <version>"
   git push -u origin changelog/<skill>-<version>
   ```

5. Open the PR against `main` titled `<skill>: changelog for <version>`, with the entry as the body. Use the available pull-request tool, or `gh pr create --base main --title "..." --body-file <file>`. If neither is available, give the user the compare URL printed by `git push`.

Never force-push, push to `main`, or include unrelated files.

## 6. Hand off

Tell the user to review and merge the PR, then run **Actions > Package skill release** for `<skill>`. That workflow builds the package and tags `<skill>@<version>`, which becomes the starting point for the next changelog.
