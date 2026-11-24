# Zenodo archival instructions: proposed v1.1.0 release

The CCF public repository is [SamAddington/ccf-coordination-benchmark](https://github.com/SamAddington/ccf-coordination-benchmark). Its historical tag `v1.0.0` has a historical DOI `10.5281/zenodo.24511437`, which **must not** be presented as the DOI for the new admission-pricing experiment.

1. Confirm the new v28 author-operated **full** rerun and archive audits are complete.
2. Confirm the candidate's MIT license applies to the source, synthetic data and generated figures and that notices exclude publisher assets and third-party code.
3. Publish the **new** immutable GitHub release tag `v1.1.0` without changing `v1.0.0`.
4. On [Zenodo's GitHub integration](https://zenodo.org/account/settings/github/), confirm the existing repository is enabled. Verify Zenodo picked up the **new** release. If it did not, follow Zenodo's release synchronization procedure; do not invent a DOI.
5. Confirm the version DOI, version title, author attribution, date, license, deposited files, and **publicly available code/data/figures** in a logged-out browser. Record the release commit and record DOI in the submission log.
6. Update the latest manuscript's Data and Code Availability with the **verified new version DOI**, preserve the historical DOI if citing its own study, and add the new DOI to `CITATION.cff` in a future development commit. Do not rewrite or repoint the published tag.

No new version DOI exists in this proposed package. A GitHub release is not third-party scientific replication.
