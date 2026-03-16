# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-03-15

### Added

- Multi-stage Dockerfile that compiles OpenSimRoot from source on Ubuntu 22.04 ARM64 (`make release`, C++14/g++)
- 480 XML input files covering 16 phenotypes x 6 environments (location x water regime)
- `scripts/entrypoint.sh` — container entrypoint that resolves XML input files from environment variables (`PHENOTYPE`, `LOCATION`, `WATER_REGIME`) and runs the simulator
- `scripts/submit-all-sims-runai.sh` — batch submission script for 96 jobs to Run:ai under the `busch-lab` project
- `.env.example` with configuration template for cluster settings
- Project documentation: README, QUICKSTART, CLAUDE.md

### Deployed

- Pushed Docker image to Docker Hub as `nntehranchi/opensimroot-drought:latest`
- Submitted first test job to the `busch-lab` project on the Salk Run:ai cluster
