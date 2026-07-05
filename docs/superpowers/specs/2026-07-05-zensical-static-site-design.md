# Design Spec: Compile ChasingHorizons with Zensical & Deploy to GitHub Pages

- **Status**: Approved
- **Author**: Antigravity
- **Date**: 2026-07-05
- **Target Custom Domain**: `travel.brainz.fun`
- **SSG Engine**: `zensical` (v0.0.46)
- **Deployment Platform**: GitHub Pages (direct deployment via GitHub Actions)

---

## 1. Overview
The goal of this project is to compile the `ChasingHorizons` repository (a guidebook of self-driving routes in China written in Markdown) into a clean, modern, and static website using `zensical` and deploy it automatically to GitHub Pages. The custom domain `travel.brainz.fun` will be bound to the deployment.

---

## 2. Architecture & File Layout

### Source & Build Structure
```
ChasingHorizons/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions deployment workflow
├── docs/                       # Original Markdown content directory
│   ├── 01_北京市.md
│   ├── ...
│   ├── SUMMARY.md              # The table of contents / source of truth
│   └── index.md                # Homepage (copied from SUMMARY.md before build)
├── site/                       # Zensical compiled static output (git-ignored)
│   ├── index.html
│   ├── CNAME                   # Generated during deployment containing custom domain
│   └── ...
├── scripts/
│   └── build_site.sh           # Local build/serve helper script
└── zensical.toml               # Zensical configuration file
```

---

## 3. Configuration & Compilation Design

### 3.1 Zensical Configuration (`zensical.toml`)
We will create `zensical.toml` in the repository root to configure the build metadata, styling, and search options.

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

### 3.2 Homepage Syncing
Since `docs/SUMMARY.md` is the existing index and contains the welcome intro and full table of contents, we will copy it to `docs/index.md` before compiling. This avoids duplication:
*   **Locally**: A helper script `scripts/build_site.sh` will handle this automatically.
*   **CI/CD**: The GitHub Actions workflow will perform this step.
*   **Git Exclusion**: We will add `docs/index.md` to `.gitignore` to avoid checking in duplicate generated content.

---

## 4. CI/CD & Deployment Flow (GitHub Actions)

We will create `.github/workflows/deploy.yml` with the following configuration:

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

---

## 5. Domain & DNS Configuration

1.  **Domain Mapping**: A `CNAME` record should be created on the registrar for `brainz.fun`:
    *   **Record Type**: `CNAME`
    *   **Host/Name**: `travel`
    *   **Value/Target**: `brainzhang-life.github.io`
2.  **GitHub Settings**: Update the Pages configuration under **Settings** -> **Pages** of the repository to select **GitHub Actions** as the build/deployment source, and specify `travel.brainz.fun` as the custom domain. Enforce HTTPS.
