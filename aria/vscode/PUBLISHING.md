# Publishing Aria to the VS Code Marketplace

The extension is packaging-ready. Publishing requires a **publisher account**
(free) that only you can create — these are the exact steps.

## One-time setup

1. **Create a publisher.** Sign in at
   <https://marketplace.visualstudio.com/manage> with a Microsoft account and
   create a publisher. Note its **ID** (e.g. `your-publisher-id`).
2. **Set the publisher in the manifest.** In `package.json`, change
   `"publisher": "aria"` to your real publisher ID. (`aria` is a placeholder and
   will not be publishable by you.)
3. **Get a Personal Access Token (PAT).** In Azure DevOps
   (<https://dev.azure.com>) → User settings → Personal access tokens → New:
   - Organization: **All accessible organizations**
   - Scopes: **Marketplace → Manage**
   Copy the token.

## Package and publish (from `aria/vscode/`)

```bash
npm install -g @vscode/vsce

# Build a .vsix you can inspect or install locally:
vsce package                       # → aria-vscode-0.1.0.vsix
code --install-extension aria-vscode-0.1.0.vsix   # optional local test

# Publish to the Marketplace:
vsce login <your-publisher-id>     # paste the PAT when prompted
vsce publish                       # or: vsce publish minor  (bumps version)
```

To also list it on the Open VSX registry (used by VSCodium, Cursor, Gitpod):

```bash
npm install -g ovsx
ovsx publish aria-vscode-0.1.0.vsix -p <open-vsx-token>
```

## Optional: publish from CI

`.github/workflows/publish-vscode-extension.yml` (in the repo root) packages the
extension on demand and publishes when you push a tag like `vscode-v0.1.0`.
Add your PAT as a repo secret named **`VSCE_PAT`** first
(Settings → Secrets and variables → Actions).

```bash
git tag vscode-v0.1.0 && git push origin vscode-v0.1.0
```

## Notes

- **License:** shipped as MIT (`LICENSE`). Change it if you want different terms.
- **Icon:** `media/icon.png` (256×256). Marketplace also shows the README
  screenshots.
- **What ships:** everything except the files in `.vscodeignore`
  (`.vscode/`, source maps, `jsconfig.json`, `.gitignore`).
- The extension is a client — users still need a running Aria server
  (`uvicorn aria.api:app`); the README explains that up front.
