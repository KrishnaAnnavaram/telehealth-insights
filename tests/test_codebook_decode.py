"""Reference problems 1, 2 and 8: skip codes as values, wrong tool columns, no codebook."""

import copy
import json
from importlib import resources

import numpy as np
import pandas as pd
import pytest

from telehealth_insights.codebook import CodebookError, load, parse
from telehealth_insights.decode import DecodeError, decode
from telehealth_insights.synthetic import generate

BASE = json.loads(
    resources.files("telehealth_insights").joinpath("data/codebook_nehrs2021.json").read_text(encoding="utf-8")
)


def test_default_codebook_roles(book):
    assert book.exposure.name == "telemedicine"
    assert [t.name for t in book.by_role("tool")] == ["telemedtool1", "telemedtool2", "telemedtool3", "telemedtool4"]
    assert len({t.label for t in book.by_role("tool")}) == 4  # each tool has its own column and label
    assert book.variables["telemedqual"].users_only and not book.variables["timedoc"].users_only
    assert set(book.missing_codes) == {-6, -7, -8, -9}


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d["variables"]["telemedqual"].update(role="target"), "role"),
        (lambda d: d["variables"]["telemedqual"].update(type="likert"), "type"),
        (lambda d: d["variables"]["telemedicine"].update(no=1), "binary"),
        (lambda d: d["variables"]["telemedqual"].update(favourable=[1, 2, 3, 4, 5]), "favourable"),
        (lambda d: d["variables"]["specialty"].update(codes=[-1, 1]), "negative"),
        (lambda d: d["missing_codes"].update({"9": "x"}), "negative"),
        (lambda d: d["design"].update(weight=None), "weight"),
        (lambda d: d["variables"]["telemedtool1"].update(role="exposure"), "exactly one exposure"),
        (lambda d: d.pop("design"), "design"),
    ],
)
def test_bad_codebooks_are_refused(change, message):
    data = copy.deepcopy(BASE)
    change(data)
    with pytest.raises(CodebookError, match=message):
        parse(data)


def test_custom_codebook_file(tmp_path):
    path = tmp_path / "cb.json"
    data = copy.deepcopy(BASE)
    data["name"] = "custom"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load(str(path)).name == "custom"


def test_no_negative_code_survives(decoded, book):
    df, rep = decoded
    numeric = df.select_dtypes("number")
    assert (numeric.fillna(0) >= 0).all().all()
    assert rep.missing["telemedqual"]["-6 not applicable (skip pattern)"] > 0
    assert any(k.startswith("-8") or k.startswith("-9") for k in rep.missing["timedoc"])


def test_users_only_items_are_empty_for_non_users(decoded):
    df, _ = decoded
    non_users = df["telemedicine"] == 0
    assert non_users.any()
    for col in ("telemedqual", "telemedsat", "telemedtool1", "telemedtool4"):
        assert df.loc[non_users, col].isna().all()
    # the prototype compared answers with skip codes: here the non-user group has no answers at all
    assert df.loc[~non_users, "telemedqual"].notna().mean() > 0.9


def test_binary_items_become_zero_one(decoded):
    df, _ = decoded
    assert set(df["telemedicine"].dropna().unique()) == {0.0, 1.0}
    assert set(df["telemedtool2"].dropna().unique()) == {0.0, 1.0}


def test_answer_from_a_non_user_is_removed_and_counted(book):
    raw = generate(300, seed=1)
    i = raw.index[raw["telemedicine"] == 2][0]
    raw.loc[i, "telemedqual"] = 5
    df, rep = decode(raw, book)
    assert np.isnan(df.loc[i, "telemedqual"]) and rep.out_of_universe["telemedqual"] == 1


def test_unknown_codes_strict_and_lenient(book):
    raw = generate(300, seed=2)
    raw.loc[0, "timedoc"] = 7
    with pytest.raises(DecodeError, match="unknown codes"):
        decode(raw, book)
    df, rep = decode(raw, book, strict=False)
    assert np.isnan(df.loc[0, "timedoc"]) and rep.unknown["timedoc"] == 1


def test_design_columns_are_checked(book):
    raw = generate(200, seed=3)
    with pytest.raises(DecodeError, match="missing columns"):
        decode(raw.drop(columns=["mailwgt"]), book)
    bad = raw.copy()
    bad.loc[0, "mailwgt"] = 0
    with pytest.raises(DecodeError, match="weights"):
        decode(bad, book)


def test_synthetic_is_seeded():
    pd.testing.assert_frame_equal(generate(500, seed=4), generate(500, seed=4))
    with pytest.raises(ValueError):
        generate(10)
