---
title: "Weekly scheduled image build and Trivy scan from main"
summary: The Trivy gate only runs on release, so a stale base image surfaces at the
  moment the release can no longer be published. A periodic build and scan from main,
  without publishing, would surface it earlier.
category: feature
created: 2026-09-09
files:
  - .github/workflows/docker-publish.yml
---

**Problem:** the blocking scan lives in the `scan` job of `docker-publish.yml`, which
triggers only on `release: published`. The base image goes stale independently of our
code: release 0.6.0 failed on 26 fixable CRITICAL/HIGH advisories in `openssl`,
`gnutls`, `krb5` and `libcap2`, all inherited from
`ghcr.io/astral-sh/uv:python3.12-bookworm-slim`, which had not been rebuilt since
2026-02-03. No commit of ours caused it, and there was no way to learn of it sooner.

**Expected:** a `schedule` trigger (weekly) builds the image from `main` on both
architectures and runs the same gate, without `build-and-push`. A stale base then shows
up as a red periodic run rather than a blocked release.

Open questions for the implementation:

- a separate workflow, or a `schedule` trigger on `docker-publish.yml` with a condition
  on the `build-and-push` job (`if: github.event_name == 'release'`);
- both `linux/amd64` and `linux/arm64` as in the release scan, or amd64 only to save
  time — arm64 under QEMU is considerably slower;
- SARIF upload: reuse the existing step with `category: trivy-image-<arch>`, or use a
  separate category so the periodic run does not overwrite the release scan's results.
