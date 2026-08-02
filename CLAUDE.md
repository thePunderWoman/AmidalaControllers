# Amidala Controllers — Claude Notes

## Design principles

**Test coverage**
- All new logic should have unit tests in `test/` to prevent regressions.
- Tests run on the native PlatformIO environment (no hardware required) — keep them that way. Do not introduce test dependencies that require Arduino or physical hardware.
- When fixing a bug, add a test that would have caught it.

**Bug fixes and regression test**
- Any time you fix a bug, that bugfix should be covered by a new regression test.

## Git workflow

**All changes must go through pull requests — never push directly to `main`.**

1. Create a feature branch, make your changes, then open a PR.
2. Push branches and create PRs with:
   ```
   git push thePunderWoman <branch>
   gh pr create ...
   ```
3. Once a PR lands, delete the local feature branch. This repo always squash or rebase merges — `main` never gets a merge commit for the PR, so `git branch -d` (and `--merged` checks) won't recognize the branch as merged even though its content has landed. Confirm via `git log --oneline` (look for the PR's commit/title on `main`) or `gh pr view <branch> --json state`, then use `git branch -D <branch>` to remove it.
