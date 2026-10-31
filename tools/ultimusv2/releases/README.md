# Releases

The built program (`PW173Editor.exe`) is **not** kept in git. Build it yourself with `build_exe.bat`, or download it from the repository's GitHub **Releases** page when one is published.

When publishing a release:
1. Build from a clean checkout, **without** a `layouts/known_files.local.json` (the build bundles the layouts folder).
2. Run the tests in `tests/` against your files first.
3. Upload `dist\PW173Editor.exe` to a new GitHub Release; note the commit it was built from.

---
[Back to the editor](../README.md)
