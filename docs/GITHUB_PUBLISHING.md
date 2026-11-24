# Upload this package to GitHub

The ZIP contains a **repository directory named `ccf-coordination-benchmark`**. Unzip it and change into that directory before running Git commands. A GitHub account and a local Git installation are needed. The following commands are examples to run **on your computer**, not steps already completed by this package.

## 1. Inspect before publishing

```bash
python3 tools/verify_release.py
python3 tools/reproduce.py --mode smoke --out ../ccf_smoke_before_publish
```

Confirm the license scope and notices. `CITATION.cff` intentionally has **no DOI** until one is actually assigned.

## 2. Create repository

Option A: Use the GitHub web UI. Create an **empty public** repository named `ccf-coordination-benchmark` without initializing a README/license/.gitignore (they are already in this package), then run:

```bash
git init -b main
git add .
git commit -m "Release CCF coordination benchmark source, data, and figures (MIT)"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/ccf-coordination-benchmark.git
git push -u origin main
```

Option B: If GitHub CLI (`gh`) is authenticated, you may create it from the directory (this **publishes publicly**):

```bash
git init -b main
git add .
git commit -m "Release CCF coordination benchmark source, data, and figures (MIT)"
gh repo create ccf-coordination-benchmark --public --source=. --remote=origin --push
```

Replace `YOUR_GITHUB_USERNAME` where used. Do not paste a personal access token into an issue, README, or chat.

## 3. Tag an immutable research snapshot

After the public repo is reviewed, create and push an annotated tag:

```bash
git tag -a v1.0.0 -m "CCF v26 verified synthetic benchmark and MIT data release"
git push origin v1.0.0
```

Then create a GitHub Release through the web UI or:

```bash
gh release create v1.0.0 --verify-tag \
  --title "CCF Coordination Benchmark v1.0.0" \
  --notes-file RELEASE_NOTES.md
```

Enabling GitHub immutable releases is optional, but once enabled, confirm assets before publication. Do not rewrite published history or reuse the tag for different experiment code/data.

## 4. DOI archiving

See [docs/ZENODO_ARCHIVING.md](ZENODO_ARCHIVING.md). Activate Zenodo for the **public repository**, and create a GitHub Release. Zenodo can assign a version DOI for the snapshot. Wait until the DOI resolves, then add that real DOI to `CITATION.cff` and the manuscript data/code availability section. Do not invent a DOI before deposit.

## 5. Verification after upload

Open the public repository in a signed-out/private browser window; check `LICENSE`, `CITATION.cff`, `fairness/results/episodes.csv`, figures, the GitHub Actions checks, and release contents. Record the **commit hash, tag, and DOI** in your research audit.
