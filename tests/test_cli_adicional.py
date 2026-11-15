"""Regressões adicionais do CLI em arquivos temporários."""

import csv
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

import pytest
from helpers import BASE, COLUMNS, run_cli


def test_reads_every_reservation(tmp_path):
    rows = [{"reservation_id": f"R-{index}"} for index in range(1, 206)]
    report = run_cli(tmp_path, rows)
    assert report["summary"]["total_reservations"] == 205
    assert report["summary"]["confirmed_reservations"] == 205
    assert report["summary"]["total_amount_brl"] == "20500.00"


def test_civil_dates_and_checkin_month(tmp_path):
    report = run_cli(tmp_path, [
        {"reservation_id": "R-1", "checkin_date": "2024-12-31", "checkout_date": "2025-01-02", "rooms": "3"},
        {"reservation_id": "R-2", "checkin_date": "2024-02-28", "checkout_date": "2024-03-01", "rooms": "2"},
    ])
    assert report["by_month"] == [
        {"month": "2024-02", "reservations": 1, "room_nights": 4, "total_brl": "100.00"},
        {"month": "2024-12", "reservations": 1, "room_nights": 6, "total_brl": "100.00"},
    ]
    assert report["summary"]["average_nightly_rate_brl"] == "20.00"


def test_non_billable_rows_do_not_create_aggregates(tmp_path):
    report = run_cli(tmp_path, [
        {"reservation_id": "R-1"},
        {"reservation_id": "R-2", "status": "CANCELLED", "hotel_id": "H02",
         "checkin_date": "2025-02-01", "checkout_date": "2025-02-04"},
        {"reservation_id": "R-3", "status": "NO_SHOW", "hotel_id": "H03",
         "checkin_date": "2025-03-01", "checkout_date": "2025-03-06"},
    ])
    assert report["summary"] == {
        "total_reservations": 3,
        "confirmed_reservations": 1,
        "cancelled_reservations": 1,
        "no_show_reservations": 1,
        "total_room_nights": 1,
        "total_amount_brl": "100.00",
        "average_nightly_rate_brl": "100.00",
    }
    assert report["by_month"] == [
        {"month": "2025-01", "reservations": 1, "room_nights": 1, "total_brl": "100.00"},
    ]
    assert report["top_hotels"] == [
        {"hotel_id": "H01", "hotel_name": "Hotel Teste", "room_nights": 1, "total_brl": "100.00"},
    ]


def test_currency_and_rounding_only_after_aggregation(tmp_path):
    report = run_cli(tmp_path, [
        {"reservation_id": "R-1", "currency": "BRL", "amount": "0.005"},
        {"reservation_id": "R-2", "currency": "USD", "amount": "0.25"},
        {"reservation_id": "R-3", "currency": "EUR", "amount": "0.01", "rooms": "2"},
    ])
    # 0.005 + 1.355 + 0.0588 = 1.4188. Arredondar as parcelas produziria 1.43.
    assert report["summary"]["total_amount_brl"] == "1.42"
    assert report["summary"]["average_nightly_rate_brl"] == "0.35"
    assert report["by_month"][0]["total_brl"] == "1.42"
    assert report["top_hotels"][0]["total_brl"] == "1.42"


def test_rank_uses_unrounded_totals_then_hotel_id(tmp_path):
    rows = [
        {"reservation_id": "R-1", "hotel_id": "H03", "amount": "10.005"},
        {"reservation_id": "R-2", "hotel_id": "H01", "amount": "10.005"},
        {"reservation_id": "R-3", "hotel_id": "H02", "amount": "10.006"},
    ]
    report = run_cli(tmp_path, rows)
    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H02", "H01", "H03"]
    assert [hotel["total_brl"] for hotel in report["top_hotels"]] == ["10.01"] * 3
    limited = run_cli(tmp_path, rows, top=1)
    assert limited["top_hotels"] == report["top_hotels"][:1]


@pytest.mark.parametrize("statuses", [[], ["NO_SHOW", "CANCELLED"]])
def test_without_confirmed_reservations(tmp_path, statuses):
    report = run_cli(tmp_path, [{"status": status} for status in statuses])
    assert report["summary"] == {
        "total_reservations": len(statuses),
        "confirmed_reservations": 0,
        "cancelled_reservations": statuses.count("CANCELLED"),
        "no_show_reservations": statuses.count("NO_SHOW"),
        "total_room_nights": 0,
        "total_amount_brl": "0.00",
        "average_nightly_rate_brl": "0.00",
    }
    assert report["by_month"] == report["top_hotels"] == []


def test_confirmed_reservation_without_nights(tmp_path):
    report = run_cli(tmp_path, [{"checkout_date": "2025-01-10", "amount": "1.005"}])
    assert report["summary"]["total_room_nights"] == 0
    assert report["summary"]["total_amount_brl"] == "1.01"
    assert report["summary"]["average_nightly_rate_brl"] == "0.00"


def test_report_types_and_fixed_offset(tmp_path):
    report = run_cli(tmp_path, [{}])
    assert set(report) == {"report_version", "generated_at", "summary", "by_month", "top_hotels"}
    assert report["report_version"] == "1.0"
    assert report["generated_at"].endswith("-03:00")
    assert datetime.fromisoformat(report["generated_at"]).utcoffset() == timedelta(hours=-3)
    summary = report["summary"]
    assert set(summary) == {
        "total_reservations", "confirmed_reservations", "cancelled_reservations",
        "no_show_reservations", "total_room_nights", "total_amount_brl", "average_nightly_rate_brl",
    }
    for field, value in summary.items():
        if field.endswith("_brl"):
            assert isinstance(value, str) and re.fullmatch(r"-?\d+\.\d{2}", value)
        else:
            assert type(value) is int


@pytest.fixture
def cli(tmp_path, monkeypatch):
    from helpers import SRC_DIR

    input_path = tmp_path / "reservas.csv"
    rates_path = tmp_path / "taxas.csv"
    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(BASE)
    rates_path.write_text("currency,rate_to_brl\nBRL,1\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(SRC_DIR))

    def execute(*args):
        return subprocess.run(
            [sys.executable, "-m", "onfly_report", *args],
            cwd=tmp_path, env=os.environ.copy(), capture_output=True, text=True, timeout=10,
        )

    return execute


@pytest.mark.parametrize("args", [
    (),
    ("--input", "reservas.csv"),
    ("--rates", "taxas.csv"),
    ("--input", "reservas.csv", "--rates", "taxas.csv", "--top", "0"),
    ("--input", "reservas.csv", "--rates", "taxas.csv", "--top", "2.5"),
    ("--input", "ausente.csv", "--rates", "taxas.csv"),
    ("--input", "reservas.csv", "--rates", "ausente.csv"),
])
def test_cli_rejects_invalid_arguments_and_missing_files(cli, args):
    result = cli(*args)
    assert result.returncode == 2
    assert result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("custom_output", [False, True])
def test_cli_creates_output_directory(cli, tmp_path, custom_output):
    path = "out/nested/report.json" if custom_output else "output/report.json"
    options = ["--output", path] if custom_output else []
    result = cli("--input", "reservas.csv", "--rates", "taxas.csv", *options)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Reservas: 1 | Confirmadas: 1 | Noites: 1 | Total BRL: 100.00"
    assert (tmp_path / path).is_file()


@pytest.mark.parametrize(("input_bytes", "rate_text"), [
    (b"\xff", "currency,rate_to_brl\nBRL,1\n"),
    (None, "currency,rate_to_brl\nBRL,NaN\n"),
    (None, "currency,rate_to_brl\nUSD,5.42\n"),
])
def test_cli_classifies_invalid_data_as_input_error(cli, tmp_path, input_bytes, rate_text):
    if input_bytes is not None:
        (tmp_path / "reservas.csv").write_bytes(input_bytes)
    (tmp_path / "taxas.csv").write_text(rate_text, encoding="utf-8")
    result = cli("--input", "reservas.csv", "--rates", "taxas.csv")
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "output/report.json").exists()


def test_cli_returns_one_when_output_cannot_be_written(cli):
    result = cli("--input", "reservas.csv", "--rates", "taxas.csv", "--output", ".")
    assert result.returncode == 1
    assert "falha ao escrever" in result.stderr
    assert result.stdout == ""
