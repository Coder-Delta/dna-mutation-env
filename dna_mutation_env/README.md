---
title: DNA Mutation OpenEnv V1
emoji: "🧬"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
  - genomics
  - bioinformatics
---

# DNA Mutation OpenEnv

Docker-based OpenEnv environment for genomic mutation analysis.

## Tasks

- `easy_snv_short_read`
- `medium_indel_low_coverage`
- `hard_repeat_structural_variant`

## Run Locally

```bash
pip install -e .
python inference.py --task-id easy_snv_short_read
python -m server.app
```

## Deploy

This directory is intended to be deployed directly with OpenEnv:

```bash
openenv validate
openenv push . --repo-id Coder-Delta/dna-mutation-env-v1
```
