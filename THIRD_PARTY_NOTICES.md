# External software, literature and notice audit

1. **`jlott22/CV_MRTA_Benchmark` (Lott and Honary).** The referenced upstream repository is MIT-licensed at pinned commit `6c7b7e5ac508a9a50cdd2938ca02c0da023c9e1e`, with copyright (c) 2026 James Lott and Vahraz Honary. Official license: <https://github.com/jlott22/CV_MRTA_Benchmark/blob/6c7b7e5ac508a9a50cdd2938ca02c0da023c9e1e/LICENSE>. The compact CCF archive does **not** contain the upstream ACBBA.py source file; its ACBBA reference is a research citation. The inventory cannot exclude unrecognized adapted fragments. If directly borrowed code is later identified, preserve the upstream full MIT notice in the relevant files or `licenses/` folder.

2. **Matplotlib.** Used to regenerate plotted figures, but its source and binary are **not** vendored in this archive. License information: <https://matplotlib.org/stable/project/license.html>. In the recorded same-host plotting environment the version was 3.10.8.

3. **CPython.** Required interpreter (3.11+ per the project README); the interpreter is not redistributed in the ZIP. The author-operated WSL2 environment reported CPython 3.14.4.

4. **Python standard-library packages.** Built-in facilities are imported; none of their implementations are separately included.

5. **References and the IEEE Access manuscript.** Research papers and the publisher's formatted template are **not bundled** in this candidate. Merely citing a paper does not license redistribution of its full text.

No external copyright assignment is inferred from references. The author affirmed original CCF source ownership and MIT licensing; any later incorporation of third-party code must honor its separate terms.
