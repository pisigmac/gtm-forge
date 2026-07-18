"""End-to-end CLI tests with an isolated home directory."""

import csv
import json
import re

from typer.testing import CliRunner

from gtm_forge.cli import app

runner = CliRunner()


def test_version(home):
    result = runner.invoke(app, ["--version"], env={"GTM_FORGE_HOME": str(home)})
    assert result.exit_code == 0
    assert "gtm-forge" in result.output


def test_init_writes_config(tmp_path):
    home = tmp_path / "fresh-home"
    result = runner.invoke(app, ["init", "--yes"], env={"GTM_FORGE_HOME": str(home)})
    assert result.exit_code == 0
    assert (home / "config.yaml").exists()


def test_skills_list(home):
    result = runner.invoke(app, ["skills", "list"], env={"GTM_FORGE_HOME": str(home)})
    assert result.exit_code == 0
    assert "experiment" in result.output


def test_experiment_flow(home):
    env = {"GTM_FORGE_HOME": str(home)}
    create = runner.invoke(
        app,
        [
            "experiment",
            "create",
            "--name",
            "Thread test",
            "--hypothesis",
            "Threads beat singles",
            "--variable",
            "format",
            "--variants",
            "single,thread",
            "--metric",
            "impressions",
        ],
        env=env,
    )
    assert create.exit_code == 0, create.output
    exp_id = re.search(r"(thread-test-[0-9a-f]{6})", create.output).group(1)

    for variant, values in (
        ("single", "100,120,110,105,115,108,112,118"),
        ("thread", "150,160,170,155,165,175,158,162"),
    ):
        add = runner.invoke(
            app, ["experiment", "add", exp_id, "--variant", variant, "--values", values], env=env
        )
        assert add.exit_code == 0, add.output

    analyze = runner.invoke(app, ["experiment", "analyze", exp_id, "--n-boot", "2000"], env=env)
    assert analyze.exit_code == 0, analyze.output
    assert "SHIP IT" in analyze.output or "INCONCLUSIVE" in analyze.output

    listing = runner.invoke(app, ["experiment", "list"], env=env)
    assert exp_id in listing.output

    decide = runner.invoke(app, ["experiment", "decide", exp_id, "--decision", "promoted"], env=env)
    assert decide.exit_code == 0


def test_eval_dry_run(home):
    result = runner.invoke(
        app,
        ["--dry-run", "eval", "--idea", "10 lessons from 100 podcast episodes"],
        env={"GTM_FORGE_HOME": str(home)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["gate"] == 90
    assert len(payload["experts"]) == 7


def test_lead_verify_disposable(home):
    result = runner.invoke(
        app, ["lead", "verify", "someone@mailinator.com"], env={"GTM_FORGE_HOME": str(home)}
    )
    assert result.exit_code == 4  # invalid/disposable exit code
    assert "disposable" in result.output


def test_lead_verify_dry_run(home):
    result = runner.invoke(app, ["--dry-run", "lead", "verify", "a@b.co"], env={"GTM_FORGE_HOME": str(home)})
    assert result.exit_code == 0
    assert "regex" in result.output


def test_seo_cannibalize(home, tmp_path):
    csv_path = tmp_path / "pages.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["url", "title", "keywords"])
        writer.writeheader()
        writer.writerow({"url": "/a", "title": "email marketing guide", "keywords": "email marketing;guide"})
        writer.writerow({"url": "/b", "title": "email marketing guide", "keywords": "email marketing;guide"})
    result = runner.invoke(
        app,
        ["seo", "cannibalize", "--csv", str(csv_path), "--threshold", "0.8"],
        env={"GTM_FORGE_HOME": str(home)},
    )
    assert result.exit_code == 0
    assert "/a" in result.output and "/b" in result.output


def test_content_calendar(home):
    result = runner.invoke(
        app,
        ["content", "calendar", "--pillars", "seo,product", "--weeks", "1"],
        env={"GTM_FORGE_HOME": str(home)},
    )
    assert result.exit_code == 0, result.output
    assert "3 posts planned" in result.output


def test_sales_health(home, tmp_path):
    csv_path = tmp_path / "deals.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "name",
                "amount",
                "stage",
                "stage_entered",
                "last_activity",
                "has_champion",
                "contacts",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "d1",
                "name": "Acme",
                "amount": "50000",
                "stage": "proposal",
                "stage_entered": "2026-07-10",
                "last_activity": "2026-07-15",
                "has_champion": "yes",
                "contacts": "3",
            }
        )
    result = runner.invoke(
        app, ["sales", "health", "--csv", str(csv_path)], env={"GTM_FORGE_HOME": str(home)}
    )
    assert result.exit_code == 0, result.output
    assert "1 deals" in result.output


def test_outbound_score(home, tmp_path):
    icp = tmp_path / "icp.yaml"
    icp.write_text("weights:\n  industry:\n    saas: 50\n", encoding="utf-8")
    leads = tmp_path / "leads.csv"
    leads.write_text("company,industry\nAcme,saas\nBeta,retail\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["outbound", "score", "--csv", str(leads), "--icp", str(icp)],
        env={"GTM_FORGE_HOME": str(home)},
    )
    assert result.exit_code == 0, result.output
    assert "Acme" in result.output


def test_costs_report(home):
    result = runner.invoke(app, ["costs", "report"], env={"GTM_FORGE_HOME": str(home)})
    assert result.exit_code == 0
    assert "Total" in result.output


def test_unknown_experiment_id_is_clean_error(home):
    env = {"GTM_FORGE_HOME": str(home)}
    for sub in (
        ["add", "--variant", "control", "--values", "1,2"],
        ["analyze"],
        ["decide", "--decision", "killed"],
    ):
        result = runner.invoke(app, ["experiment", *sub[:1], "nope-999", *sub[1:]], env=env)
        assert result.exit_code == 1, (sub, result.output)
        assert "No experiment 'nope-999'" in result.output
        assert "Traceback" not in result.output
