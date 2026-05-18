# Contributing to tierproxy/python-sdk

Thanks for considering a contribution. This SDK ships under Apache 2.0.

## Developer Certificate of Origin (DCO)

We use the [DCO](https://developercertificate.org/) instead of a CLA. Add a
`Signed-off-by:` line to every commit:

```
git commit -s -m "fix: handle 429 retry"
```

## Local setup

```bash
git clone https://github.com/tierproxy/python-sdk
cd python-sdk
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

External contributors can run `pytest -m mocked_e2e` for end-to-end tests
against a mock gateway. Tests marked `requires_real_gateway` need a
`TIERPROXY_API_KEY` (only TierProxy maintainers have one for the staging
gateway).

## Pull requests

1. Fork, branch from `main` as `feat/<name>` or `fix/<name>`.
2. Make changes; add tests.
3. Sign commits (`git commit -s`).
4. `pytest -q` locally.
5. Open the PR. CI runs `test`, `openapi-lint`, `brand-leak-gate`.
6. A maintainer reviews. Once approved + green, it merges via squash.

## Issues

- Bug? Use the bug template.
- Feature idea? Use the feature template.
- Security report? See `SECURITY.md` — do NOT open a public issue.
