from pathlib import Path

import pytest

from gmail_cleaner.core import (
    candidate_from_message,
    extract_one_click_url,
    group_candidates,
    header_map,
    is_protected_sender,
    read_approvals,
    write_review_csv,
)


def headers(**values: str):
    return [{"name": name.replace("_", "-"), "value": value} for name, value in values.items()]


def test_extracts_only_authenticated_one_click_https():
    mapped = header_map(
        headers(
            List_Unsubscribe="<mailto:bye@example.com>, <https://news.example/u/token>",
            List_Unsubscribe_Post="List-Unsubscribe=One-Click",
            Authentication_Results="mx.google.com; dkim=pass header.i=@example.com",
            DKIM_Signature="v=1; h=From:Subject:List-Unsubscribe:List-Unsubscribe-Post; b=abc",
        )
    )
    assert extract_one_click_url(mapped) == "https://news.example/u/token"


@pytest.mark.parametrize(
    "changed",
    [
        {"List_Unsubscribe_Post": ""},
        {"Authentication_Results": "dkim=fail"},
        {"DKIM_Signature": "v=1; h=From:Subject; b=abc"},
        {"List_Unsubscribe": "<http://news.example/u/token>"},
    ],
)
def test_rejects_unsafe_or_unverified_unsubscribe(changed):
    values = {
        "List_Unsubscribe": "<https://news.example/u/token>",
        "List_Unsubscribe_Post": "List-Unsubscribe=One-Click",
        "Authentication_Results": "dkim=pass",
        "DKIM_Signature": "v=1; h=List-Unsubscribe:List-Unsubscribe-Post; b=abc",
    }
    values.update(changed)
    assert extract_one_click_url(header_map(headers(**values))) is None


def test_candidate_respects_important_and_protected_sender():
    base = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["CATEGORY_PROMOTIONS", "IMPORTANT"],
        "payload": {"headers": headers(From="News <news@example.com>", Subject="Oferta")},
    }
    assert candidate_from_message(base, protected_label_ids=set(), protected_senders=[]) is None

    base["labelIds"] = ["CATEGORY_PROMOTIONS"]
    assert (
        candidate_from_message(base, protected_label_ids=set(), protected_senders=["@example.com"])
        is None
    )


def test_groups_and_csv_are_deny_by_default(tmp_path: Path):
    messages = []
    for index in range(2):
        message = {
            "id": f"m{index}",
            "threadId": f"t{index}",
            "labelIds": ["SPAM"],
            "payload": {
                "headers": headers(From="Basura <spam@example.com>", Subject=f"Spam {index}")
            },
        }
        messages.append(
            candidate_from_message(message, protected_label_ids=set(), protected_senders=[])
        )
    groups = group_candidates(item for item in messages if item)
    assert len(groups) == 1
    assert groups[0].count == 2

    review = tmp_path / "review.csv"
    write_review_csv(review, groups)
    assert read_approvals(review)[groups[0].key] == (False, False)


def test_exact_or_domain_sender_protection():
    assert is_protected_sender("boss@example.com", ["boss@example.com"])
    assert is_protected_sender("alerts@bank.example", ["@bank.example"])
    assert not is_protected_sender("fake@bank.example.evil", ["@bank.example"])
