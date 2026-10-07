# data/

Git ignores every file in this folder except this README. Do not commit survey files.

## Real data: NEHRS 2021 physician public-use file

| Item | Value |
|---|---|
| Name | National Electronic Health Records Survey (NEHRS) 2021, physician public-use file |
| Publisher | CDC National Center for Health Statistics (NCHS) |
| Source | <https://www.cdc.gov/nchs/nehrs/> (public-use data files and documentation) |
| Terms | NCHS public-use data. Read the NCHS data use agreement on the source page. Do not try to identify a respondent |
| Expected file | `data/NEHRS2021.csv` (any path works with `--data` or `TELEHEALTH_DATA`) |

Download the codebook and the survey documentation together with the data file.

## Columns that the default codebook expects

The bundled codebook (`src/telehealth_insights/data/codebook_nehrs2021.json`) names these columns.
The names and codes are working assumptions from an earlier export. Check them against the official
codebook. If they differ, copy the JSON file, edit it and set `TELEHEALTH_CODEBOOK`.

| Column | Role | Codes in the default codebook |
|---|---|---|
| `phyid_p` | respondent ID | text |
| `mailwgt` | survey weight | number above 0 |
| `strat_p` | stratum | any code |
| `telemedicine` | exposure | 1 = yes, 2 = no |
| `telemedqual` | outcome, users only | 1 to 5, favourable = 4, 5 |
| `telemedsat` | outcome, users only | 1 to 5, favourable = 4, 5 |
| `timedoc` | outcome, all physicians | 1 to 5, favourable (high time) = 4, 5 |
| `telemedtool1` to `telemedtool4` | tools, users only | 1 = yes, 2 = no |
| `specialty`, `practice_size`, `setting` | controls | category codes |

Negative values are missing codes: -6 not applicable, -7 not ascertained, -8 do not know, -9 refused or blank.

## Synthetic data (no download)

`telehealth-insights synth --rows 4000 --out data/synthetic_nehrs.csv` writes fake survey rows with the same
columns and skip logic. With no `--data` and no `TELEHEALTH_DATA`, `analyze` generates them in memory.
