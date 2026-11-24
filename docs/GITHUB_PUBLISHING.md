# Publish this snapshot as the next version of an EXISTING GitHub repository

**Repository:** `SamAddington/ccf-coordination-benchmark`  
**Existing published tag:** `v1.0.0` — do not delete or repoint it.  
**Proposed new tag:** `v1.1.0` — not yet published.  
**New DOI:** none; wait for Zenodo to archive the new release.

The ZIP contains a full directory `ccf-coordination-benchmark`. **Do not create a second repository** and do not upload the ZIP as one file in the Git tree.

## Stage and test locally

```bash
unzip CCF_v28_GitHub_v1.1.0_Candidate_20261124.zip
cd ccf-coordination-benchmark
python3 tools/verify_release.py
python3 tools/reproduce_v28.py --mode smoke --out ../ccf_v28_smoke_before_release_01
```

Make sure all 119+ manifest files pass and the smoke report succeeds. Run `--mode full` on your separate author-controlled computer and retain the full output, logs, and signed attestation before publishing a citable release.

## Update the existing GitHub repository

Use a fresh local clone (requires Git authentication and author approval):

```bash
git clone https://github.com/SamAddington/ccf-coordination-benchmark.git existing-ccf
cd existing-ccf
git checkout main
```

Copy the **contents** of the extracted candidate `ccf-coordination-benchmark/` into this clone, including the hidden `.github/` and `.gitignore` files. Review `git status --short`, run `python3 tools/verify_release.py`, and inspect `git diff --stat` and the full changes. **Do not accidentally delete pre-existing repository files that are not part of the candidate**. If source files on GitHub changed after this snapshot, reconcile them instead of blindly overwriting.

```bash
git add -A
git commit -m "Add admission-pricing experiments and reproduction evidence (v1.1.0)"
git push origin main
```

**Only after approving the complete version:**

```bash
git tag -a v1.1.0 -m "CCF admission-pricing benchmark v1.1.0"
git push origin v1.1.0
gh release create v1.1.0 --verify-tag \
  --title "CCF Coordination Benchmark v1.1.0 — Admission Pricing and Client Policy" \
  --notes-file RELEASE_NOTES.md
```

## Zenodo / manuscript

Check Zenodo GitHub integration is enabled. Verify Zenodo published a **new version** for tag `v1.1.0` with the correct file contents and MIT license. Use its **actual version DOI**, not the historical `10.5281/zenodo.24511437`, for the new manuscript. After the DOI resolves publicly, update `CITATION.cff` on the continuing development branch, and update the manuscript availability statement with the real link. Do not retarget the immutable release tag to include this subsequent citation update.

See `docs/ZENODO_ARCHIVING.md` and `RELEASE_STATUS.md` for caveats. No repository write or DOI publication is performed by this packaging step.
