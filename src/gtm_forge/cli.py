"""Command-line interface: `gtm <command>`.

Global flags:
  --config PATH   use a specific config.yaml
  --dry-run       print the plan (commands, prompts, estimated cost) without executing
  --version       print version and exit
"""

from __future__ import annotations

import csv
import getpass
import json
import shutil
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from gtm_forge import __version__
from gtm_forge.config import Settings, config_path, load_settings, save_settings
from gtm_forge.core.context import RunContext
from gtm_forge.core.credentials import resolve_secret, store_secret
from gtm_forge.core.state import StateStore
from gtm_forge.core.updater import check_for_update, self_update
from gtm_forge.llm.factory import build_provider
from gtm_forge.skills import SKILLS
from gtm_forge.skills.content_eval.panel import dry_run_plan as eval_dry_run
from gtm_forge.skills.content_eval.panel import run_panel
from gtm_forge.skills.contentops.calendar import (
    deterministic_calendar,
    llm_calendar,
    render_markdown,
)
from gtm_forge.skills.growth.engine import (
    Experiment,
    add_observations,
    analyze_experiment,
    create_experiment,
    decide,
    list_experiments,
    load_experiment,
    save_experiment,
)
from gtm_forge.skills.leads.dossier import build_dossier, collect_facts
from gtm_forge.skills.leads.enrich import verify_cascade
from gtm_forge.skills.outbound.icp import ICPConfig, score_lead, score_leads
from gtm_forge.skills.outbound.sequences import generate_sequence
from gtm_forge.skills.sales.champions import Champion, draft_message, find_reengagement_targets
from gtm_forge.skills.sales.health import Deal, portfolio_health
from gtm_forge.skills.seo.brief import Page, brief_dry_run, build_brief, find_cannibals
from gtm_forge.skills.video import pipeline as video_pipeline

app = typer.Typer(
    name="gtm",
    help="GTM Forge: production-grade, config-driven GTM and AI marketing skills.",
    no_args_is_help=True,
)
experiment_app = typer.Typer(help="Growth experiments with real statistics.", no_args_is_help=True)
seo_app = typer.Typer(help="SEO operations.", no_args_is_help=True)
lead_app = typer.Typer(help="Lead intelligence.", no_args_is_help=True)
outbound_app = typer.Typer(help="Outbound engine.", no_args_is_help=True)
video_app = typer.Typer(help="Video clip pipeline.", no_args_is_help=True)
content_app = typer.Typer(help="Content operations.", no_args_is_help=True)
sales_app = typer.Typer(help="Sales pipeline.", no_args_is_help=True)
skills_app = typer.Typer(help="Agent skill files.", no_args_is_help=True)
keys_app = typer.Typer(help="Secret storage via the OS keychain.", no_args_is_help=True)
costs_app = typer.Typer(help="Cost ledger.", no_args_is_help=True)

app.add_typer(experiment_app, name="experiment")
app.add_typer(seo_app, name="seo")
app.add_typer(lead_app, name="lead")
app.add_typer(outbound_app, name="outbound")
app.add_typer(video_app, name="video")
app.add_typer(content_app, name="content")
app.add_typer(sales_app, name="sales")
app.add_typer(skills_app, name="skills")
app.add_typer(keys_app, name="keys")
app.add_typer(costs_app, name="costs")


def emit(*objects: object) -> None:
    """Render rich output through click's echo so it is capturable everywhere."""
    console = Console()
    with console.capture() as capture:
        console.print(*objects)
    typer.echo(capture.get(), nl=False)


_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def _version_cb(value: bool) -> None:
    if value:
        emit(f"gtm-forge {__version__}")
        raise typer.Exit


@app.callback()
def main(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", help="Path to config.yaml."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only; no external calls or writes."),
    version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True, help="Print version and exit."
    ),
) -> None:
    settings = load_settings(config)
    state = StateStore(settings.paths.state_db)
    ctx.obj = {"settings": settings, "state": state, "dry_run": dry_run}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _begin(ctx: typer.Context, skill: str, command: str) -> RunContext:
    rc = RunContext(
        settings=ctx.obj["settings"],
        state=ctx.obj["state"],
        dry_run=ctx.obj["dry_run"],
        skill=skill,
    )
    return rc.begin(command)


def _out(ctx: typer.Context, *parts: str) -> Path:
    target = ctx.obj["settings"].paths.output_dir.joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _provider_and_model(ctx: typer.Context, rc: RunContext):
    settings: Settings = ctx.obj["settings"]
    provider = build_provider(settings, ctx.obj["state"], rc.run_id)
    return provider, settings.llm.resolved_model()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _finish(rc: RunContext) -> None:
    rc.end("success")


# ---------------------------------------------------------------------------
# setup & diagnostics
# ---------------------------------------------------------------------------


@app.command()
def init(
    provider: str = typer.Option("anthropic", "--provider", help="anthropic | openai | ollama"),
    model: str | None = typer.Option(None, "--model", help="Model name; blank = provider default."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Accept defaults, skip prompts."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing config."),
) -> None:
    """Interactive setup wizard. Writes ~/.gtm-forge/config.yaml."""
    target = config_path()
    if target.exists() and not force:
        emit(f"[yellow]Config already exists at {target}. Use --force to overwrite.[/yellow]")
        raise typer.Exit(1)
    settings = Settings()
    if not yes:
        provider = typer.prompt("LLM provider (anthropic/openai/ollama)", default=provider)
        model = typer.prompt("Model (blank for provider default)", default=model or "") or None
        budget = typer.prompt("Per-run USD budget (blank for none)", default="")
        if budget:
            settings.costs.budget_usd_per_run = float(budget)
    settings.llm.provider = provider
    settings.llm.model = model or None
    path = save_settings(settings)
    emit(f"[green]Wrote {path}[/green]")
    emit("Next: run [bold]gtm doctor[/bold] to verify your setup.")


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Verify configuration, credentials, and local tooling."""
    settings: Settings = ctx.obj["settings"]
    state: StateStore = ctx.obj["state"]
    table = Table(title="gtm-forge doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    critical_failed = False

    def row(name: str, ok: bool, detail: str, critical: bool = False) -> None:
        nonlocal critical_failed
        table.add_row(name, "[green]ok[/green]" if ok else "[red]fail[/red]", detail)
        if critical and not ok:
            critical_failed = True

    row("config", True, str(config_path()), critical=True)

    try:
        state.kv_set("doctor_probe", "ok")
        row("state db", True, str(state.path), critical=True)
    except Exception as exc:  # noqa: BLE001
        row("state db", False, str(exc), critical=True)

    provider = settings.llm.provider
    if provider == "ollama":
        row("llm credentials", True, "ollama is local; no key needed", critical=True)
    else:
        env_name = settings.llm.api_key_env or _KEY_ENV.get(provider, "")
        ok = resolve_secret(env_name) is not None
        row("llm credentials", ok, f"env {env_name}", critical=True)

    ffmpeg = shutil.which(settings.video.ffmpeg_bin)
    row("ffmpeg", ffmpeg is not None, ffmpeg or f"'{settings.video.ffmpeg_bin}' not on PATH")
    whisper = shutil.which(settings.video.whisper_bin)
    row("whisper (optional)", whisper is not None, whisper or "needed only for local transcription")

    info = check_for_update(__version__)
    detail = (
        f"latest {info.latest} — update available"
        if info.update_available
        else (f"up to date ({info.current})" if info.latest else (info.error or "unknown"))
    )
    row("version", not info.update_available, detail)

    emit(table)
    if critical_failed:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# costs
# ---------------------------------------------------------------------------


@costs_app.command("report")
def costs_report(ctx: typer.Context) -> None:
    """Aggregated LLM spend by model."""
    state: StateStore = ctx.obj["state"]
    table = Table(title="LLM cost ledger")
    for col in ("Model", "Calls", "Input tokens", "Output tokens", "Cost (USD)"):
        table.add_column(col)
    total = 0.0
    for row_ in state.costs_summary():
        total += float(row_["cost_usd"])
        table.add_row(
            str(row_["model"]),
            str(row_["calls"]),
            f"{row_['input_tokens']:,}",
            f"{row_['output_tokens']:,}",
            f"${row_['cost_usd']:.4f}",
        )
    emit(table)
    emit(f"[bold]Total: ${total:.4f}[/bold]")


@costs_app.command("runs")
def costs_runs(ctx: typer.Context, limit: int = typer.Option(20, "--limit")) -> None:
    """Recent runs with status."""
    state: StateStore = ctx.obj["state"]
    table = Table(title="Recent runs")
    for col in ("Run ID", "Skill", "Command", "Status", "Dry", "Started"):
        table.add_column(col)
    for row_ in state.list_runs(limit):
        table.add_row(
            str(row_["run_id"]),
            str(row_["skill"]),
            str(row_["command"]),
            str(row_["status"]),
            "yes" if row_["dry_run"] else "no",
            str(row_["started_at"])[:19],
        )
    emit(table)


# ---------------------------------------------------------------------------
# update / keys / skills
# ---------------------------------------------------------------------------


@app.command()
def update(check_only: bool = typer.Option(False, "--check", help="Only check; do not upgrade.")) -> None:
    """Check for a newer release and upgrade the installed package."""
    info = check_for_update(__version__)
    if info.error:
        emit(f"[yellow]Update check failed: {info.error}[/yellow]")
    elif not info.update_available:
        emit(f"[green]gtm-forge {info.current} is up to date.[/green]")
    if not info.update_available:
        return
    emit(f"Update available: {info.current} -> {info.latest} ({info.url})")
    if check_only:
        return
    ok, message = self_update()
    emit(message)
    if not ok:
        raise typer.Exit(1)


@keys_app.command("set")
def keys_set(name: str = typer.Argument(..., help="Secret name, e.g. ANTHROPIC_API_KEY")) -> None:
    """Store a secret in the OS keychain (requires the 'keyring' package)."""
    value = getpass.getpass(f"Value for {name}: ")
    if store_secret("gtm-forge", name, value):
        emit(f"[green]Stored {name} in the OS keychain (service: gtm-forge).[/green]")
    else:
        emit(
            "[yellow]keyring is not installed. Install it (pip install keyring) "
            f"or use: export {name}=<value>[/yellow]"
        )
        raise typer.Exit(1)


@skills_app.command("list")
def skills_list() -> None:
    """List the built-in skills."""
    table = Table(title="gtm-forge skills")
    table.add_column("Skill")
    table.add_column("What it does")
    for name, desc in SKILLS.items():
        table.add_row(name, desc)
    emit(table)


@skills_app.command("install")
def skills_install(
    dest: Path = typer.Option(Path(".claude/skills"), "--dest", help="Where to write SKILL.md files."),
) -> None:
    """Copy agent-readable SKILL.md files into your project."""
    from importlib.resources import files

    src = files("gtm_forge").joinpath("skills-md")
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in src.iterdir():
        if item.name.endswith(".md"):
            (dest / item.name).write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
            count += 1
    emit(f"[green]Installed {count} skill files into {dest}[/green]")


# ---------------------------------------------------------------------------
# experiment
# ---------------------------------------------------------------------------


def _load_experiment_or_exit(ctx: typer.Context, exp_id: str) -> Experiment:
    """Load an experiment or exit cleanly — a bad ID is user error, not a traceback."""
    try:
        return load_experiment(_out(ctx), exp_id)
    except FileNotFoundError as exc:
        emit(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@experiment_app.command("create")
def experiment_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    hypothesis: str = typer.Option(..., "--hypothesis"),
    variable: str = typer.Option(..., "--variable", help="The single thing you are changing."),
    variants: str = typer.Option(..., "--variants", help="Comma-separated; FIRST is the control."),
    metric: str = typer.Option(..., "--metric", help="The number you are moving."),
) -> None:
    rc = _begin(ctx, "experiment", "create")
    exp = create_experiment(
        _out(ctx),
        name=name,
        hypothesis=hypothesis,
        variable=variable,
        variants=[v.strip() for v in variants.split(",") if v.strip()],
        metric=metric,
    )
    emit(f"[green]Experiment created:[/green] {exp.id} (status: {exp.status})")
    emit(f"Add data: gtm experiment add {exp.id} --variant {exp.variants[0]} --values 10,12,11")
    _finish(rc)


@experiment_app.command("add")
def experiment_add(
    ctx: typer.Context,
    exp_id: str = typer.Argument(...),
    variant: str = typer.Option(..., "--variant"),
    values: str = typer.Option("", "--values", help="Comma-separated numbers."),
    csv_path: Path | None = typer.Option(None, "--csv", help="CSV with columns: variant,value"),
) -> None:
    rc = _begin(ctx, "experiment", "add")
    exp = _load_experiment_or_exit(ctx, exp_id)
    collected: dict[str, list[float]] = {}
    if csv_path:
        for row_ in _read_csv(csv_path):
            collected.setdefault(row_["variant"], []).append(float(row_["value"]))
    if values:
        collected.setdefault(variant, []).extend(float(v) for v in values.split(",") if v.strip())
    if not collected:
        emit("[yellow]Nothing to add. Pass --values or --csv.[/yellow]")
        raise typer.Exit(1)
    for var, vals in collected.items():
        add_observations(exp, var, vals)
    save_experiment(ctx.obj["settings"].paths.output_dir, exp)
    emit(
        f"[green]Added observations to {exp.id}:[/green] "
        + ", ".join(f"{k} +{len(v)}" for k, v in collected.items())
    )
    _finish(rc)


@experiment_app.command("analyze")
def experiment_analyze(
    ctx: typer.Context,
    exp_id: str = typer.Argument(...),
    alpha: float = typer.Option(0.05, "--alpha"),
    n_boot: int = typer.Option(5000, "--n-boot"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    rc = _begin(ctx, "experiment", "analyze")
    exp = _load_experiment_or_exit(ctx, exp_id)
    try:
        reports = analyze_experiment(exp, alpha=alpha, n_boot=n_boot, seed=seed)
    except ValueError as exc:
        emit(f"[red]{exc}[/red]")
        rc.fail(str(exc))
        raise typer.Exit(1) from exc
    for variant, report in reports.items():
        emit(f"\n[bold]{variant}[/bold] vs control (n={report.n_treatment} vs {report.n_control})")
        emit(report.verdict)
    _finish(rc)


@experiment_app.command("list")
def experiment_list(ctx: typer.Context) -> None:
    experiments = list_experiments(_out(ctx))
    if not experiments:
        emit("No experiments yet. Create one with [bold]gtm experiment create[/bold].")
        return
    table = Table(title="Experiments")
    for col in ("ID", "Name", "Metric", "Variants", "Status"):
        table.add_column(col)
    for exp in experiments:
        table.add_row(exp.id, exp.name, exp.metric, ", ".join(exp.variants), exp.status)
    emit(table)


@experiment_app.command("decide")
def experiment_decide(
    ctx: typer.Context,
    exp_id: str = typer.Argument(...),
    decision: str = typer.Option(..., "--decision", help="promoted | killed"),
) -> None:
    rc = _begin(ctx, "experiment", "decide")
    exp = _load_experiment_or_exit(ctx, exp_id)
    decide(exp, decision)
    save_experiment(ctx.obj["settings"].paths.output_dir, exp)
    emit(f"[green]{exp_id} marked as {exp.status}.[/green]")
    _finish(rc)


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------


@app.command("eval")
def eval_cmd(
    ctx: typer.Context,
    idea: str = typer.Option(..., "--idea", help="The content idea to score."),
    context_file: Path | None = typer.Option(None, "--context", help="Text with audience, platform, goals."),
    gate: int = typer.Option(90, "--gate", help="Minimum panel mean to pass."),
    out: Path | None = typer.Option(None, "--out", help="Where to write the markdown report."),
) -> None:
    """Score a content idea with the expert panel. Exit code 3 = below gate (revise)."""
    rc = _begin(ctx, "eval", "run")
    context = context_file.read_text(encoding="utf-8") if context_file else ""
    if ctx.obj["dry_run"]:
        typer.echo(json.dumps(eval_dry_run(idea, context, gate)))
        _finish(rc)
        return
    provider, model = _provider_and_model(ctx, rc)
    try:
        report = run_panel(provider, idea=idea, context=context, gate=gate, model=model)
    except Exception as exc:  # noqa: BLE001
        rc.fail(str(exc))
        raise
    markdown = report.to_markdown()
    emit(markdown)
    target = out or (_out(ctx, "evals") / f"{rc.run_id}.md")
    target.write_text(markdown, encoding="utf-8")
    emit(f"\n[dim]Report written to {target}[/dim]")
    _finish(rc)
    if not report.passed:
        raise typer.Exit(3)


# ---------------------------------------------------------------------------
# seo
# ---------------------------------------------------------------------------


@seo_app.command("brief")
def seo_brief(
    ctx: typer.Context,
    keyword: str = typer.Option(..., "--keyword"),
    audience: str = typer.Option(..., "--audience"),
    serp_notes: Path | None = typer.Option(
        None, "--serp-notes", help="Text file with current SERP observations."
    ),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    rc = _begin(ctx, "seo", "brief")
    notes = serp_notes.read_text(encoding="utf-8") if serp_notes else ""
    if ctx.obj["dry_run"]:
        typer.echo(json.dumps(brief_dry_run(keyword, audience, notes)))
        _finish(rc)
        return
    provider, model = _provider_and_model(ctx, rc)
    markdown = build_brief(provider, keyword=keyword, audience=audience, serp_notes=notes, model=model)
    target = out or (_out(ctx, "seo") / f"{keyword.lower().replace(' ', '-')}.md")
    target.write_text(markdown, encoding="utf-8")
    emit(markdown)
    emit(f"\n[dim]Brief written to {target}[/dim]")
    _finish(rc)


@seo_app.command("cannibalize")
def seo_cannibalize(
    ctx: typer.Context,
    csv_path: Path = typer.Option(..., "--csv", help="Columns: url,title,keywords (semicolon-separated)."),
    threshold: float = typer.Option(0.6, "--threshold"),
) -> None:
    rc = _begin(ctx, "seo", "cannibalize")
    pages = [
        Page(
            url=r["url"],
            title=r.get("title", ""),
            keywords=[k.strip() for k in r.get("keywords", "").split(";") if k.strip()],
        )
        for r in _read_csv(csv_path)
    ]
    conflicts = find_cannibals(pages, threshold=threshold)
    if not conflicts:
        emit(f"[green]No cannibalization above threshold {threshold}.[/green]")
    else:
        table = Table(title=f"Cannibalization conflicts (threshold {threshold})")
        for col in ("Page A", "Page B", "Similarity", "Shared tokens"):
            table.add_column(col)
        for c in conflicts:
            table.add_row(c.url_a, c.url_b, f"{c.similarity:.2f}", ", ".join(c.shared_tokens[:8]))
        emit(table)
    _finish(rc)


# ---------------------------------------------------------------------------
# video
# ---------------------------------------------------------------------------


@video_app.command("clips")
def video_clips(
    ctx: typer.Context,
    src: Path = typer.Option(..., "--src", exists=True, help="Long-form video file."),
    count: int = typer.Option(4, "--count", help="Number of clips to produce."),
    out_dir: Path | None = typer.Option(None, "--out", help="Clip output directory."),
) -> None:
    """Transcribe, score, and cut a long-form video into standalone clips."""
    settings: Settings = ctx.obj["settings"]
    rc = _begin(ctx, "video", "clips")
    work = (out_dir or _out(ctx, "clips")) / "_work"
    wav = work / "audio.wav"
    whisper_base = work / "transcript"

    if ctx.obj["dry_run"]:
        plan = rc.plan(
            steps=[
                video_pipeline.shlex.join(
                    video_pipeline.extract_audio_command(src, wav, settings.video.ffmpeg_bin)
                ),
                video_pipeline.shlex.join(video_pipeline.whisper_command(settings.video, wav, whisper_base)),
                "LLM scores transcript windows and picks the best clips",
                f"ffmpeg cuts up to {count} clips into {work.parent}",
            ]
        )
        typer.echo(json.dumps(plan))
        _finish(rc)
        return

    ffmpeg = shutil.which(settings.video.ffmpeg_bin)
    whisper = shutil.which(settings.video.whisper_bin)
    if not ffmpeg or not whisper:
        message = (
            "Missing tools. Need both ffmpeg and a whisper.cpp binary on PATH. "
            f"ffmpeg: {'found' if ffmpeg else 'MISSING'}; "
            f"whisper: {'found' if whisper else 'MISSING'}. "
            "Set video.ffmpeg_bin / video.whisper_bin in config.yaml."
        )
        rc.fail(message)
        emit(f"[red]{message}[/red]")
        raise typer.Exit(1)

    work.mkdir(parents=True, exist_ok=True)
    video_pipeline.run_commands([video_pipeline.extract_audio_command(src, wav, settings.video.ffmpeg_bin)])
    video_pipeline.run_commands([video_pipeline.whisper_command(settings.video, wav, whisper_base)])
    transcript_json = whisper_base.with_suffix(".json")
    segments = video_pipeline.parse_whisper_json(transcript_json.read_text(encoding="utf-8"))
    windows = video_pipeline.chunk_segments(segments, settings.video.window_seconds)
    emit(f"Transcribed {len(segments)} segments into {len(windows)} scoring windows.")

    provider, model = _provider_and_model(ctx, rc)
    clips = video_pipeline.score_windows(provider, windows, clip_count=count, model=model)
    commands = video_pipeline.build_cut_commands(src, clips, work.parent, settings.video.ffmpeg_bin)
    video_pipeline.run_commands(commands)
    manifest = work.parent / "manifest.json"
    manifest.write_text(
        json.dumps(
            [
                {"start_s": c.start_s, "end_s": c.end_s, "score": c.score, "hook": c.hook, "output": c.output}
                for c in clips
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    table = Table(title="Clips")
    for col in ("#", "Start", "End", "Score", "Hook"):
        table.add_column(col)
    for i, c in enumerate(clips, 1):
        table.add_row(str(i), f"{c.start_s:.1f}s", f"{c.end_s:.1f}s", str(c.score), c.hook)
    emit(table)
    emit(f"[dim]Manifest: {manifest}[/dim]")
    _finish(rc)


# ---------------------------------------------------------------------------
# lead
# ---------------------------------------------------------------------------


@lead_app.command("dossier")
def lead_dossier(
    ctx: typer.Context,
    company: str = typer.Option(..., "--company"),
    url: str = typer.Option(..., "--url"),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    rc = _begin(ctx, "lead", "dossier")
    if ctx.obj["dry_run"]:
        plan = rc.plan(
            steps=[
                f"Fetch {url} and capture status, title, meta description",
                "Detect tech stack from HTML and headers (heuristics)",
                "Extract buying signals: hiring, emails, socials",
                "LLM writes a ranked account brief from the facts",
            ]
        )
        typer.echo(json.dumps(plan))
        _finish(rc)
        return
    settings: Settings = ctx.obj["settings"]
    facts = collect_facts(url, timeout_s=settings.leads.http_timeout_s)
    provider, model = _provider_and_model(ctx, rc)
    markdown = build_dossier(provider, company=company, facts=facts, model=model)
    target = out or (_out(ctx, "dossiers") / f"{company.lower().replace(' ', '-')}.md")
    target.write_text(markdown, encoding="utf-8")
    emit(markdown)
    emit(f"\n[dim]Dossier written to {target}[/dim]")
    _finish(rc)


@lead_app.command("verify")
def lead_verify(
    ctx: typer.Context,
    email: str = typer.Argument(...),
) -> None:
    """Verify an email through the configured provider cascade. Exit 4 = invalid/disposable."""
    settings: Settings = ctx.obj["settings"]
    rc = _begin(ctx, "lead", "verify")
    if ctx.obj["dry_run"]:
        plan = rc.plan(
            steps=[f"Try provider: {name}" for name in settings.leads.email_providers],
            note="First conclusive answer wins; providers without API keys report 'unknown' and are skipped.",
        )
        typer.echo(json.dumps(plan))
        _finish(rc)
        return
    final, trail = verify_cascade(
        email, settings.leads.email_providers, timeout_s=settings.leads.http_timeout_s
    )
    table = Table(title=f"Verification: {email}")
    for col in ("Provider", "Status", "Detail"):
        table.add_column(col)
    for result in trail:
        table.add_row(result.provider, result.status, result.detail)
    emit(table)
    emit(f"[bold]Verdict: {final.status}[/bold]")
    _finish(rc)
    if final.status in {"invalid", "disposable"}:
        raise typer.Exit(4)


# ---------------------------------------------------------------------------
# outbound
# ---------------------------------------------------------------------------


@outbound_app.command("score")
def outbound_score(
    ctx: typer.Context,
    csv_path: Path = typer.Option(..., "--csv", help="Lead rows; headers become scoring fields."),
    icp: Path = typer.Option(..., "--icp", help="ICP weights YAML."),
    out: Path | None = typer.Option(None, "--out", help="Write ranked CSV here."),
) -> None:
    rc = _begin(ctx, "outbound", "score")
    config = ICPConfig.from_yaml(icp)
    ranked = score_leads(_read_csv(csv_path), config)
    table = Table(title="ICP ranking")
    table.add_column("Rank")
    table.add_column("Lead")
    table.add_column("Score")
    table.add_column("Label")
    for i, (lead, breakdown) in enumerate(ranked[:20], 1):
        name = lead.get("company") or lead.get("name") or lead.get("email") or f"row {i}"
        table.add_row(str(i), name, f"{breakdown.total:g}", breakdown.label)
    emit(table)
    if out and ranked:
        with out.open("w", newline="", encoding="utf-8") as fh:
            fieldnames = list(ranked[0][0].keys()) + ["icp_score", "icp_label"]
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for lead, breakdown in ranked:
                writer.writerow({**lead, "icp_score": breakdown.total, "icp_label": breakdown.label})
        emit(f"[dim]Ranked CSV written to {out}[/dim]")
    _finish(rc)


@outbound_app.command("sequence")
def outbound_sequence(
    ctx: typer.Context,
    icp: Path = typer.Option(..., "--icp"),
    lead_json: str = typer.Option(..., "--lead-json", help='e.g. {"company":"Acme","industry":"saas"}'),
    steps: int = typer.Option(5, "--steps"),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    rc = _begin(ctx, "outbound", "sequence")
    lead = json.loads(lead_json)
    config = ICPConfig.from_yaml(icp)
    breakdown = score_lead(lead, config)
    emit(f"ICP fit: {breakdown.total:g} ({breakdown.label}) — {'; '.join(breakdown.reasons) or 'no signals'}")
    if ctx.obj["dry_run"]:
        plan = rc.plan(steps=[f"Generate a {steps}-step sequence referencing the fit reasons above"])
        typer.echo(json.dumps(plan))
        _finish(rc)
        return
    provider, model = _provider_and_model(ctx, rc)
    sequence = generate_sequence(provider, lead=lead, breakdown=breakdown, steps=steps, model=model)
    lines = [f"# Sequence for {lead.get('company', 'lead')}", ""]
    for step in sequence:
        lines.append(f"## Day {step.day} — {step.channel} (step {step.step})")
        if step.subject:
            lines.append(f"**Subject:** {step.subject}")
        lines += ["", step.body, ""]
    markdown = "\n".join(lines)
    target = out or (_out(ctx, "sequences") / "sequence.md")
    target.write_text(markdown, encoding="utf-8")
    emit(markdown)
    emit(f"\n[dim]Sequence written to {target}[/dim]")
    _finish(rc)


# ---------------------------------------------------------------------------
# content
# ---------------------------------------------------------------------------


@content_app.command("calendar")
def content_calendar(
    ctx: typer.Context,
    pillars: str = typer.Option(..., "--pillars", help="Comma-separated content pillars."),
    weeks: int = typer.Option(4, "--weeks"),
    per_week: int = typer.Option(3, "--per-week"),
    mode: str = typer.Option("deterministic", "--mode", help="deterministic | llm"),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    rc = _begin(ctx, "content", "calendar")
    pillar_list = [p.strip() for p in pillars.split(",") if p.strip()]
    if mode == "llm" and not ctx.obj["dry_run"]:
        provider, model = _provider_and_model(ctx, rc)
        entries = llm_calendar(provider, pillar_list, weeks=weeks, posts_per_week=per_week, model=model)
    else:
        entries = deterministic_calendar(pillar_list, weeks=weeks, posts_per_week=per_week)
    markdown = render_markdown(entries)
    target = out or (_out(ctx, "content") / "calendar.md")
    target.write_text(markdown, encoding="utf-8")
    emit(f"[green]{len(entries)} posts planned.[/green] Calendar: {target}")
    _finish(rc)


# ---------------------------------------------------------------------------
# sales
# ---------------------------------------------------------------------------


@sales_app.command("health")
def sales_health(
    ctx: typer.Context,
    csv_path: Path = typer.Option(
        ..., "--csv", help="Columns: id,name,amount,stage,stage_entered,last_activity,has_champion,contacts"
    ),
) -> None:
    rc = _begin(ctx, "sales", "health")
    deals = [
        Deal(
            id=r["id"],
            name=r["name"],
            amount=float(r["amount"]),
            stage=r["stage"],
            stage_entered=date.fromisoformat(r["stage_entered"]),
            last_activity=date.fromisoformat(r["last_activity"]),
            has_champion=r.get("has_champion", "").strip().lower() in {"1", "true", "yes"},
            contacts=int(r.get("contacts", "1") or 1),
        )
        for r in _read_csv(csv_path)
    ]
    summary = portfolio_health(deals)
    tiers = summary["tiers"]
    emit(
        f"[bold]{summary['total_deals']} deals[/bold] — healthy {tiers['healthy']}, "
        f"at-risk {tiers['at-risk']}, critical {tiers['critical']}. "
        f"At-risk amount: ${summary['at_risk_amount']:,.0f}"
    )
    table = Table(title="Deal health (worst first)")
    for col in ("Deal", "Risk", "Tier", "Why"):
        table.add_column(col)
    for report in summary["reports"]:
        table.add_row(report.name, str(report.risk), report.tier, "; ".join(report.reasons) or "—")
    emit(table)
    _finish(rc)


@sales_app.command("champions")
def sales_champions(
    ctx: typer.Context,
    csv_path: Path = typer.Option(
        ..., "--csv", help="Columns: name,old_company,status,new_company,role,last_deal"
    ),
    draft: bool = typer.Option(False, "--draft", help="Draft re-engagement notes with the LLM."),
    limit: int = typer.Option(5, "--limit"),
) -> None:
    rc = _begin(ctx, "sales", "champions")
    champions = [
        Champion(
            name=r["name"],
            old_company=r.get("old_company", ""),
            status=r.get("status", ""),
            new_company=r.get("new_company", ""),
            role=r.get("role", ""),
            last_deal=r.get("last_deal", ""),
        )
        for r in _read_csv(csv_path)
    ]
    targets = find_reengagement_targets(champions)
    table = Table(title="Re-engagement targets")
    for col in ("Champion", "New company", "Priority", "Reason"):
        table.add_column(col)
    for t in targets:
        table.add_row(t.champion.name, t.champion.new_company or "?", t.priority, t.reason)
    emit(table)
    if draft and targets and not ctx.obj["dry_run"]:
        provider, model = _provider_and_model(ctx, rc)
        for t in targets[:limit]:
            emit(f"\n[bold]{t.champion.name}[/bold]")
            emit(draft_message(provider, target=t, model=model))
    _finish(rc)


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@app.command()
def serve(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8420, "--port"),
) -> None:
    """Run the REST API (requires: pip install 'gtm-forge[serve]')."""
    try:
        import uvicorn
    except ImportError:
        emit("[red]Missing server dependencies. Run: pip install 'gtm-forge[serve]'[/red]")
        raise typer.Exit(1) from None
    from gtm_forge.serve import create_app

    uvicorn.run(
        create_app(settings=ctx.obj["settings"], state=ctx.obj["state"]),
        host=host,
        port=port,
    )
