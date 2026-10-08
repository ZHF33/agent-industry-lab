# Contributing

Open an issue describing the change, then submit a focused pull request.

- Include synthetic examples and relevant verification results.
- Keep secrets, personal information, databases and generated runtime files out of commits.
- Distinguish planned, prototype, offline-tested, model-tested and platform-tested behavior.
- Preserve human review for business actions; do not add automatic production publishing.
- Keep third-party copyright notices and document dependency licenses.
- Contributions are provided under the repository MIT license.

From the repository root, install requirements.lock and run:
```powershell
python -m pytest tests examples/travel-triage/test_triage.py -q
```
Run Bakery tests separately from examples/bakery-agent:
```powershell
python -m pytest tests -q
```
GitHub Actions are disabled; include local test results with the pull request.
