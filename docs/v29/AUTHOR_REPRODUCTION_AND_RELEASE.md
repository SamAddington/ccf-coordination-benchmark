# Author-controlled full reproduction and publication gate

The archived source/data and numerical checks were executed in the manuscript-authoring computational environment. This procedure does not authenticate a person or host. A full **author-operated** rerun on a separate machine is pending.

## Ubuntu / WSL2

1. Download the candidate repository ZIP and its SHA-256 sidecar and verify with `sha256sum -c <filename>.zip.sha256` from their directory.
2. Unzip the candidate. In the extracted `ccf-coordination-benchmark` root, run:

```bash
python3 --version  # 3.11 or newer
python3 tools/verify_release.py
python3 tools/reproduce_v29.py --mode smoke --out ../ccf_v29_smoke_01 \
  --operator "Samuel Addington" --machine-description "AMD 7945HX, Ubuntu Linux (WSL2)"
```

3. For the full source replay, use a **different, previously nonexistent** output path:

```bash
python3 tools/reproduce_v29.py --mode full --out ../ccf_v29_full_01 \
  --operator "Samuel Addington" --machine-description "AMD 7945HX, Ubuntu Linux (WSL2)"
```

The runner checks the historical 12,816 v28 admission/guard episodes and the additional 1,728 settlement/delay controls, then reconstructs Supplementary Tables S1–S3 exactly from stored evidence. Earlier v1.0.0 historical data remain in the tree and can be reproduced separately with `python3 tools/reproduce.py --mode full --out ../ccf_v26_full_01`.

4. Check `../ccf_v29_full_01/reproduction_result.json` for status `MATCHED__OPERATOR_AND_MACHINE_SELF_REPORTED` and verify all log exits. If a result has `FAILED_OR_INCOMPLETE`, do not report successful reproduction; inspect the logs. The `smoke` mode only verifies subsets and cannot substitute for the complete run.
5. Preserve the raw results directory unmodified, complete a factual attestation with date, hardware, OS, Python version and signature, and archive it:

```bash
cd ..
tar -czf ccf_v29_author_full_evidence.tar.gz ccf_v29_full_01
sha256sum ccf_v29_author_full_evidence.tar.gz > ccf_v29_author_full_evidence.tar.gz.sha256
```

Upload the evidence TAR, hash sidecar and completed attestation for auditing. No true independent **third-party** replication can be claimed from a self-reported author run.

## GitHub / Zenodo

Preserve public `v1.0.0` and its Zenodo DOI. After author verification, commit the **contents** of this candidate to `main` under MIT, check `.github/workflows/reproducibility.yml`, issue a fresh tagged release `v1.1.0`, and verify its tag is fixed to the intended commit. Enable Zenodo's GitHub integration to archive that tag, obtain and verify the **version-specific** DOI and all deposited files, then update the manuscript's availability statement and `CITATION.cff` with the verified DOI. Do not replace the published historical DOI or invent one.

The repository source is research code; its reproducibility does not validate a deployed service or physical network.
