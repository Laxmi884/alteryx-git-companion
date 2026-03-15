# Alteryx Git Companion — Claude Code Instructions

## Release Workflow (GitHub Actions)

The release workflow (`.github/workflows/release.yml`) builds `AlterxyGitCompanion.exe` on a Windows runner and uploads it to GitHub Releases.

### How to trigger a release

Push a `v*` tag from **any branch** — the workflow triggers on tag pushes, not branch pushes:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The tag does **not** need to be on `main`. It reads whatever commit the tag points to.

### Known CI quirks (already fixed — do not revert)

**1. `npm ci --legacy-peer-deps`**
`@tailwindcss/vite` declares peer support for Vite ≤7, but the project uses Vite 8. The flag suppresses the peer conflict. The build works correctly — this is a metadata mismatch, not a real incompatibility.

**2. 4-part version format for `pyivf-make_version`**
The tool requires `X.Y.Z.W` (four numeric parts). Git tags are `vX.Y.Z`, so the workflow strips the `v` prefix and appends `.0`:
```powershell
$version = "$env:TAG_NAME".TrimStart('v') + ".0"
```
Do not pass the raw tag directly — it will fail with a `ValidationError`.

**3. `permissions: contents: write` on the job**
Required for `softprops/action-gh-release` to create and upload GitHub Releases. Without it the upload fails with a `403 Resource not accessible by integration` error.
