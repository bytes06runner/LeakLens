# Integrations

| Integration | File | Status |
|---|---|---|
| pre-commit hook | [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml) | static scan of staged `.py` / `.ipynb` files; verified with `pre-commit try-repo` (tests/test_integrations.py records the command) |
| GitHub Action | [`action.yml`](../action.yml) | composite action: install, scan, SARIF upload to code scanning; exercised by `.github/workflows/leaklens-selfcheck.yml` |

Both run the **static** analyser only. They never execute the code they scan.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/bytes06runner/LeakLens
    rev: main   # pin a commit
    hooks:
      - id: leaklens
```

```yaml
# .github/workflows/leakage.yml
permissions: {contents: read, security-events: write}
jobs:
  leaklens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bytes06runner/LeakLens@main
        with: {paths: "notebooks src", fail-on: high}
```
