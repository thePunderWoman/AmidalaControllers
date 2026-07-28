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
