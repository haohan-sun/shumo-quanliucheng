# License: not yet chosen

This repository does **not** currently carry an open-source license.

The original workspace never declared one, and a license cannot be inferred from
public availability. Choosing a license is the repository owner's decision, so no
license text has been added here.

## What this means today

- GitHub's default copyright rules apply: the code is publicly readable, but no
  permission to copy, modify, or redistribute it has been granted.
- Until a license is chosen, treat this repository as **all rights reserved**.
  Do not assume MIT, Apache-2.0, GPL, or any other terms.
- This also affects vendored or referenced material: see
  [`UPSTREAM_SOURCES.md`](90_工具与配置/third_party/UPSTREAM_SOURCES.md) for the
  third-party surface and the license recorded for each entry.

## How to resolve it

1. Pick a license. If you have no preference, widely used options are:
   - **MIT** — permissive, shortest, most common for tooling templates;
   - **Apache-2.0** — permissive, adds an explicit patent grant;
   - **GPL-3.0** — copyleft, requires derivatives to stay open.
2. Add the full license text as `LICENSE` in the repository root.
3. Update this file to state the chosen license, or delete it and reference
   `LICENSE` from `README.md`.
4. If the intent is to keep the tooling permissive but the CUMCM paper skill
   (`90_工具与配置/.agents/skills/mm-cumcm-paper-writing-review/`) under different
   terms, say so explicitly rather than leaving it implicit.

## Third-party material already in the tree

| Where | What | Recorded license |
| --- | --- | --- |
| `90_工具与配置/.agents/skills/context-optimization/` | Skill files from an upstream context-engineering project, tracked verbatim | permissive upstream license, recorded with the commit hash in `CODEX_CAPABILITIES.md` |
| `90_工具与配置/.agents/skills/mm-mathematical-derivation/references/methodology-sources.md` | Method inspiration only, no text copied | MIT sources listed individually |
| `90_工具与配置/third_party/UPSTREAM_SOURCES.md` | Design-review log for architecture research | see that file |
| `90_工具与配置/templates/cumcmthesis(1).cls` | LaTeX class file used as a working template | verify against the contest's current rules before redistribution |

None of these entries authorises redistributing this repository as a whole; that
still depends on the owner's license choice above.
