# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A multimedia-database (CSDLĐPT / MMDB) course project: a curated dataset of **655 one-shot percussion WAVs in 13 classes**, a Vietnamese LaTeX report, and a feature database + top-5 similarity search + web demo for requirements 3–5. Docs, code identifiers, and commit-facing prose are in Vietnamese; keep new text in Vietnamese and match the existing naming style (`tinh_dac_trung`, `CayKD`, `ma_tep`…).

Four parts, in pipeline order:

1. `percussion_filter.py` (root) — original offline filter: scans a source dataset, does signal checks, keyword labelling (`ALIASES` table at top of file), SHA-256/PCM dedup, and **copies** into a new output dir (`accepted/`, `review/`, CSVs). `analyze_audio.py` cross-checks labels with the CLAP model (separate heavy env, `requirements-model.txt`).
2. `filtered_output/` — the frozen, curated deliverable (655 files). `accepted.csv` is metadata; `evidence/` holds hashes/inventory/selection; `features/` holds feature sets A (21-dim), B (39-dim), C (60-dim, standardized A+B). Treat as read-only; never point the filter tool's `--output` at it.
3. `bao_cao_bo_go/` — the report. `bao_cao_mmdb.tex` is the full report (req. 1–4 — req. 5 is the live demo, not written up; self-contained, tables embedded); its Parts I–II are a copy of the submitted `bao_cao_mmdb_yeu_cau_1_2.tex` (keep that file frozen). `bao_cao_mmdb_yeu_cau_3_4.tex` is the standalone req. 3–4 report: Parts III–IV copied from `bao_cao_mmdb.tex` with numbering continued (counters set to Mục 13 / Bảng 11 / Hình 2) and refs into Parts I–II written as literal numbers — apply any Part III–IV edit to both files. Figures in `hinh/`: `hinh1`–`hinh2` from `ve_hinh_minh_hoa.py`, `hinh3`–`hinh6` from `csdl_tim_kiem/minh_hoa.py` (PNG copies for Word via `pdftoppm -r 200`); the UML figures `III_03_*`, `IV_04_*`, `IV_05_*` are exported from `so_do_uml/*.puml` with Visual Paradigm. The PTIT-format Word version of the req. 3–4 report is built from `word/input.md` by `word/build_report.py` (equations via pandoc) — `input.md` is hand-maintained, so apply Part III–IV edits there too. `trich_xuat_dac_trung.py` **defines the feature algorithm**; `tai_lap_dac_trung_655.py` re-runs it and rewrites `filtered_output/features/`.
4. `csdl_tim_kiem/` — requirements 3–4. `dac_trung.py` imports `bao_cao_bo_go/trich_xuat_dac_trung.py` via `sys.path` and reuses it verbatim, so DB values match `filtered_output/features/` exactly. Changing the feature code in `bao_cao_bo_go/` therefore changes both the report numbers and the search DB. `csdl.py` holds the PostgreSQL + pgvector schema (server from root `compose.yaml`, `localhost:5433`, override with `CSDL_URL`). Search has three modes: `pgvector` (default, SQL `ORDER BY u <-> q`), `cay_kd` (hand-written k-d tree, `cay_kd.py`) and `vet_can` (brute force). pgvector stores float32, so float64 vectors are rebuilt from `raw_features` + `normalization_params`; the k-d tree uses them, and the pgvector path takes 2k SQL candidates and re-ranks them in float64. All three modes return identical results. `tim_kiem.py` is the CLI (default set **C**); `giao_dien.py` + `web/` is the local web demo (req. 5); `danh_gia.py` writes `ket_qua_danh_gia/` (also HNSW recall, unseen-instrument label distribution, timings); `minh_hoa.py` writes `minh_hoa.json` + report figures. `truy_van_thu/` holds 77 query files not in the DB (73 unseen-instrument, 4 new known-class) copied from the Freesound download by `chuan_bi_truy_van_thu.py`. Numbers in Parts III–IV of the report come from these outputs — rerun and update the `.tex` together.

The DB is not committed: after `docker compose up -d --wait`, run `xay_dung_csdl.py` (drops and recreates all tables). `dac_trung.kiem_tra_tin_hieu` implements the report's Section 2 signal checks (same definitions as `bao_cao_bo_go/kiem_ke_am_thanh.py`) and runs on both the 655 stored files and every query; its measurements go to table `signal_checks`, whose `CHECK` constraints mirror the thresholds. Key invariants in the search code: query normalization uses the **stored** μ/s (never recomputed); ties break by smaller `ma_tep` so the k-d tree and brute force return identical lists (a test enforces this); a query whose PCM hash matches a DB file excludes that file.

## Commands

Run from repo root. The analysis/search env is `.venv-audio` (Python 3.11+); the filter tool uses `.venv`.

```sh
# Search / DB (requirements 3–4) — needs Docker running
docker compose up -d --wait
.venv-audio/bin/python -m pip install -r csdl_tim_kiem/requirements.txt
.venv-audio/bin/python csdl_tim_kiem/xay_dung_csdl.py              # (re)build PostgreSQL tables (~3 s)
.venv-audio/bin/python csdl_tim_kiem/tim_kiem.py q.wav [--bo A|B|C] [--cach pgvector|cay_kd|vet_can] [--json]
.venv-audio/bin/python csdl_tim_kiem/giao_dien.py                   # web demo, http://127.0.0.1:8765
.venv-audio/bin/python csdl_tim_kiem/danh_gia.py                    # evaluation (~40 s)
.venv-audio/bin/python csdl_tim_kiem/minh_hoa.py                    # 4b intermediate values + figures 3-6
.venv-audio/bin/python -m pytest csdl_tim_kiem/kiem_thu.py csdl_tim_kiem/test_giao_dien.py   # 17 tests
.venv-audio/bin/python -m pytest csdl_tim_kiem/kiem_thu.py::test_cay_kd_giong_vet_can   # single test

# Filter tool tests (synthetic audio, unittest)
python -m unittest -v test_percussion_filter.py

# Re-derive features (overwrites filtered_output/features/, not the .tex)
.venv-audio/bin/python bao_cao_bo_go/tai_lap_dac_trung_655.py

# Build the report — XeLaTeX or Tectonic only, never pdfLaTeX (fontspec + Vietnamese)
tectonic --outdir bao_cao_bo_go bao_cao_bo_go/bao_cao_mmdb.tex
```

## Report editing rules

- Edit the `.tex` directly. Don't recreate or run old report generators (`tao_bao_cao*.py`, `cap_nhat_bao_cao_mmdb.py`; gitignored) — they would overwrite hand edits.
- When numbers change, take them from the regenerated tables in `filtered_output/features/` / `evidence/`.
- Content the group explicitly excluded from the report: licence information, manual-listening claims, number of rejected files, lecturer slide citations, and any claim of accuracy on an independent test set.
- Review notes and change summaries live in `review/`.
- Workflow: work on a branch and open a PR (all prior changes merged via PRs).
