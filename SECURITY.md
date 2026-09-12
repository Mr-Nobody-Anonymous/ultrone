# Security Policy

## Supported versions

Ultrone is a research platform under active development. Security fixes are
applied to the `main` branch only.

## Reporting a vulnerability

Please report vulnerabilities privately via the GitHub security advisories
feature for this repository:

https://github.com/Mr-Nobody-Anonymous/ultrone/security/advisories

Please do **not** open a public issue about a potential security
vulnerability.

Include:
- a description of the issue,
- steps or a proof-of-concept to reproduce it,
- the potential impact.

You should receive a response within a few days.

## Scope notes

Ultrone is **simulation-only**. The following are explicitly out of scope
and will not be fixed as security issues:

- Attacks that require connecting the platform to live weapon systems,
  live brokers, or real operational data — such connections violate the
  project's core constraints and are not supported configurations.
- The public Gradio demo (`deploy/hf_space/`) running with untrusted
  inputs beyond documented abuse of free hosting quotas.

## Hardening expectations for deployments

- The Ultron server (`server.py`) is designed for research use. If you
  expose it, put it behind an authenticating reverse proxy.
- Secrets belong in environment variables (`.env` is gitignored), never in
  committed files.
