"""Command line: synth | codebook | decode | analyze."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from telehealth_insights.analyses import run_all
from telehealth_insights.codebook import CodebookError, load
from telehealth_insights.config import Settings, load_env_file
from telehealth_insights.decode import DecodeError, decode
from telehealth_insights.report import write
from telehealth_insights.synthetic import generate


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="telehealth-insights", description=__doc__)
    ap.add_argument("--env-file", default=".env")
    ap.add_argument("--codebook", help="codebook JSON (default TELEHEALTH_CODEBOOK, else the bundled NEHRS 2021 file)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("synth", help="write a synthetic survey CSV")
    p.add_argument("--rows", type=int, default=4000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="data/synthetic_nehrs.csv")

    sub.add_parser("codebook", help="print the variables of the codebook")

    p = sub.add_parser("decode", help="decode a CSV and print the missing-code report")
    p.add_argument("csv")
    p.add_argument("--lenient", action="store_true", help="unknown codes become NaN instead of an error")

    p = sub.add_parser("analyze", help="run Q1 to Q3 and write report.md, results.json and charts")
    p.add_argument("--data", help="survey CSV (default TELEHEALTH_DATA, else synthetic rows)")
    p.add_argument("--rows", type=int, default=4000)
    p.add_argument("--seed", type=int)
    p.add_argument("--lenient", action="store_true")
    p.add_argument("--out", help="report folder (default TELEHEALTH_OUTPUT or reports/latest)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(args.env_file)
    try:
        settings = Settings.from_env()
        book = load(args.codebook or settings.codebook_path)
        return _run(args, settings, book)
    except (CodebookError, DecodeError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run(args, settings: Settings, book) -> int:
    if args.cmd == "synth":
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        generate(args.rows, seed=args.seed).to_csv(out, index=False)
        print(f"wrote {args.rows} synthetic rows to {out}")
        return 0

    if args.cmd == "codebook":
        print(f"{book.name}\n{book.verify}\ndesign: weight={book.weight} strata={book.strata} psu={book.psu}")
        for v in book.variables.values():
            extra = f" favourable={list(v.favourable)}" if v.favourable else ""
            print(f"  {v.name:14s} {v.role:8s} {v.type:11s} {v.universe:20s} {v.label}{extra}")
        return 0

    if args.cmd == "decode":
        _, rep = decode(pd.read_csv(args.csv), book, strict=not args.lenient)
        print(rep.summary())
        return 0

    if args.cmd == "analyze":
        path = args.data or settings.data_path
        seed = settings.seed if args.seed is None else args.seed
        if path:
            raw, source = pd.read_csv(path), path
        else:
            raw, source = generate(args.rows, seed=seed), f"synthetic(n={args.rows}, seed={seed})"
        df, rep = decode(raw, book, strict=not args.lenient)
        results = run_all(df, book, settings.alpha)
        out = write(args.out or settings.output_dir, results, book, source, rep.summary())
        share = results["describe"]["telemedicine_share"]
        print(f"data: {source}")
        print(f"telemedicine share: {share['value']:.3f} [{share['ci_low']:.3f}, {share['ci_high']:.3f}]")
        for t in results["tests"]:
            print(f"  {t['outcome']:12s} {t['term']:13s} {t['effect']:31s} {t['estimate']:+.3f} "
                  f"[{t['ci_low']:+.3f}, {t['ci_high']:+.3f}] p={t['p_value']:.4f} holm={t['p_holm']:.4f}")
        print(f"wrote {out / 'report.md'}")
        return 0
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
