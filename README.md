# snake-migrator

`snake-migrator` is a migration helper for RobotPy/semiwrap projects that are moving generated APIs from camelCase and WPILib-style enum names to Pythonic `snake_case` and `CAPS_CASE` names.

The installed Python package is `snake_case_migration`. The command-line entry point is `snake-case-migration`, and the module can also be run with `python -m snake_case_migration`.

## Installation

From this repository:

```bash
python -m pip install -e .
```

To run the test suite, install the test extra first:

```bash
python -m pip install -e '.[test]'
python -m pytest
```

## How the tool works

The migration is driven by a TOML manifest. By default the CLI reads and writes `snake_case_migration.toml` in the current working directory; use `--manifest PATH` to choose a different file.

A manifest contains:

- `config.known_words`: terms that should stay grouped during name conversion. This list is the only source of known words used by scans; if it is omitted, scans use an empty list.
- `[[mapping]]`: old-to-new name mappings. Mappings record the name kind, old name, new name, source, optional reason, and scope.
- `[[ignored]]`: names that should not be reported by audit.
- `[[semiwrap_bug]]`: notes for migration issues caused by semiwrap behavior rather than project code.

Mappings and ignores can be global or scoped to a directory. Scoped entries only apply to files under that path, which lets one manifest handle multiple RobotPy subprojects.

## Typical workflow

1. Create or validate a manifest:

   ```bash
   snake-case-migration manifest init
   snake-case-migration manifest check
   ```

2. Update semiwrap projects so generated bindings use snake-case output:

   ```bash
   snake-case-migration pyproject path/to/pyproject.toml
   snake-case-migration pyproject --write path/to/pyproject.toml
   ```

   Without `--write`, the command prints files that would change. With `--write`, it adds or updates:

   - `tool.semiwrap.name_transform.default = "snake_case"`
   - `tool.semiwrap.name_transform.enum_value = "CAPS_CASE"`
   - `tool.semiwrap.name_transform.known_words = []`

3. Scan existing Python code to add generated mappings to the manifest:

   ```bash
   snake-case-migration scan-py --write src tests examples
   ```

4. Scan constants that should become final `CAPS_CASE` enum or constant names:

   ```bash
   snake-case-migration scan-caps-constants --write src
   ```

5. Rewrite Python code using the manifest mappings:

   ```bash
   snake-case-migration rewrite-py src tests examples
   snake-case-migration rewrite-py --write src tests examples
   ```

6. Rewrite documentation, examples, and other text files:

   ```bash
   snake-case-migration rewrite-text docs examples
   snake-case-migration rewrite-text --write docs examples
   ```

7. Audit for remaining old-style names:

   ```bash
   snake-case-migration audit src tests examples
   ```

   `audit` exits with status `1` if it finds remaining old-style names and `0` otherwise.

## Command behavior

All rewriting commands are dry-run by default. In dry-run mode they print the paths or mappings that would change and do not modify files. Add `--write` to persist changes.

`rewrite-py` uses LibCST so it can update definitions, calls, attributes, and keyword arguments while preserving formatting. `rewrite-text` performs identifier-aware text replacements and avoids cascading replacements. `audit` checks Python files, stubs, and semiwrap YAML for mapped old names or unmapped camelCase candidates that still need attention.
