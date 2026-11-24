# Zenodo DOI archiving for the GitHub release

GitHub source hosting and a Zenodo DOI are complementary. This package contains `CITATION.cff` for GitHub's citation UI and Zenodo metadata. Its DOI field is intentionally absent until a real archive exists.

1. Publish the **public** GitHub repository with the MIT license and all referenced source/data files.
2. Log in to [Zenodo](https://zenodo.org/) and connect your GitHub account.
3. From Zenodo's GitHub integration, **enable** `ccf-coordination-benchmark` (sync if it does not appear).
4. **After enabling Zenodo integration**, publish the GitHub release tagged `v1.0.0` (or another documented tag). Zenodo normally ingests enabled releases and assigns a DOI.
5. Confirm the repository name, title, license, author, and public file contents on the Zenodo record. Verify the **version-specific DOI** in a logged-out browser.
6. Include that DOI in `CITATION.cff` and the submission manuscript's Data and Code Availability statement, and preserve which Git commit and release it identifies. Do not retroactively change the archived release files in place.

Useful official references:
- https://help.zenodo.org/docs/github/enable-repository/
- https://help.zenodo.org/docs/github/describe-software/
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files

A pre-release artifact does not imply a registered DOI. The DOI and GitHub URLs must be verified **after** publishing.
