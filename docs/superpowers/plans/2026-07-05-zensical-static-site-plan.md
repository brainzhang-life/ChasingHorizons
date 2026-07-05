# Zensical Static Site Compilation & GitHub Pages Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile the `ChasingHorizons` repository into a static documentation website using `zensical` and deploy it to GitHub Pages with the custom domain `travel.brainz.fun`.

**Architecture:** Create a `zensical.toml` configuration file, automate homepage syncing (`docs/SUMMARY.md` -> `docs/index.md`), and set up a GitHub Actions workflow to build and deploy the compiled `site/` files directly to GitHub Pages with OIDC authentication.

**Tech Stack:** `zensical` (v0.0.46), Python (v3.10), GitHub Actions.

## Global Constraints
- Target Custom Domain: `travel.brainz.fun`
- SSG Engine: `zensical` (v0.0.46)
- Deployment Platform: GitHub Pages (direct deployment via GitHub Actions)
- Deployment trigger: Push to the `main` branch.

---

### Task 1: Zensical Configuration & Git Ignore Update

**Files:**
- Create: `zensical.toml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `docs/SUMMARY.md` and all markdown guidebooks in `docs/`.
- Produces: Compiled `site/` folder (upon running `zensical build`).

- [ ] **Step 1: Update `.gitignore` to exclude generated site artifacts and the synchronized homepage**

Update `.gitignore` to ensure the build output directory `site/` and the temporary synchronized homepage `docs/index.md` are not tracked. Add the following lines to the end of [`.gitignore`](file:///opt/brainzhang/ChasingHorizons/.gitignore):

```
# Zensical build output
/site

# Zensical generated homepage
/docs/index.md
```

- [ ] **Step 2: Create Zensical configuration file `zensical.toml`**

Create [`zensical.toml`](file:///opt/brainzhang/ChasingHorizons/zensical.toml) in the root of the repository with the following exact content:

```toml
[project]
site_name = "追光而行：中国绝美自驾路线规划指南"
site_description = "专为自驾游爱好者打造的保姆级路线指南，覆盖中国全部 34 个省级行政区。"
site_url = "https://travel.brainz.fun"
site_dir = "site"

[project.theme]
language = "zh"
features = [
    "content.code.copy",
    "content.code.select",
    "navigation.footer",
    "navigation.instant",
    "search.highlight",
]

[[project.theme.palette]]
media = "(prefers-color-scheme: light)"
scheme = "default"
primary = "deep orange"
accent = "blue"

[[project.theme.palette]]
media = "(prefers-color-scheme: dark)"
scheme = "slate"
primary = "deep orange"
accent = "blue"
```

- [ ] **Step 3: Manually copy `SUMMARY.md` to `index.md` for verification**

Run the copy command to create the homepage file:
Run: `cp docs/SUMMARY.md docs/index.md`

- [ ] **Step 4: Verify the build locally**

Run the build command to verify that Zensical successfully compiles the documentation:
Run: `zensical build --clean`
Expected: Output showing successful compilation and the generation of `site/index.html` and other assets. Check that `site/index.html` exists.
Run: `ls site/index.html`
Expected: `site/index.html` is listed.

- [ ] **Step 5: Clean up the generated files and commit**

Remove the manually created `docs/index.md` and `site/` folder, then stage and commit:
Run: `rm -f docs/index.md && rm -rf site/`
Run: `git add .gitignore zensical.toml`
Run: `git commit -m "chore: add zensical configuration and update .gitignore"`

---

### Task 2: Local Build and Serve Script

**Files:**
- Create: `scripts/build_site.sh`

**Interfaces:**
- Consumes: `docs/SUMMARY.md` and `zensical.toml`.
- Produces: Executable shell script `scripts/build_site.sh` that automates local preview.

- [ ] **Step 1: Create the local build/serve script**

Create [`scripts/build_site.sh`](file:///opt/brainzhang/ChasingHorizons/scripts/build_site.sh) with the following exact content:

```bash
#!/bin/bash
set -e

# Sync SUMMARY.md to index.md
echo "Syncing docs/SUMMARY.md to docs/index.md..."
cp docs/SUMMARY.md docs/index.md

# Handle commands
if [ "$1" = "serve" ]; then
    echo "Starting local Zensical preview server..."
    zensical serve
else
    echo "Building static site..."
    zensical build --clean
fi
```

- [ ] **Step 2: Make the script executable**

Run: `chmod +x scripts/build_site.sh`

- [ ] **Step 3: Verify the script works**

Run: `./scripts/build_site.sh`
Expected: Output shows "Syncing docs/SUMMARY.md to docs/index.md...", followed by "Building static site..." and successful compilation logs.
Verify `site/index.html` is created.
Run: `ls site/index.html`
Expected: `site/index.html` is listed.

- [ ] **Step 4: Clean up generated files and commit**

Run: `rm -f docs/index.md && rm -rf site/`
Run: `git add scripts/build_site.sh`
Run: `git commit -m "feat: add build_site.sh script for local preview and compilation"`

---

### Task 3: GitHub Actions Deployment Workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: Push to `main` branch.
- Produces: Direct deployment artifact and deployment to GitHub Pages.

- [ ] **Step 1: Create the GitHub Actions deployment workflow**

Create [`.github/workflows/deploy.yml`](file:///opt/brainzhang/ChasingHorizons/.github/workflows/deploy.yml) with the following exact content:

```yaml
name: Deploy Zensical Site to GitHub Pages

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: Install Zensical
        run: |
          python -m pip install --upgrade pip
          pip install zensical

      - name: Sync Homepage Content
        run: cp docs/SUMMARY.md docs/index.md

      - name: Build Site
        run: zensical build

      - name: Configure CNAME for GitHub Pages
        run: echo "travel.brainz.fun" > site/CNAME

      - name: Upload Pages Artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: 'site'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit the deployment workflow**

Stage the newly created workflow and commit:
Run: `git add .github/workflows/deploy.yml`
Run: `git commit -m "ci: add GitHub Actions workflow to deploy site to GitHub Pages"`
