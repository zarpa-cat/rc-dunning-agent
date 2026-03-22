import typer
from rich.console import Console
from rich.table import Table

from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.engine import DunningEngine
from rc_dunning_agent.analytics import RecoveryAnalytics

app = typer.Typer(name="rda", help="RC Dunning Agent - automated payment recovery manager")
console = Console()

DB_PATH = "./dunning.db"


def _get_engine(db_path: str = DB_PATH) -> DunningEngine:
    store = DunningStore(db_path)
    return DunningEngine(store)


@app.command("list")
def list_records(db_path: str = typer.Option(DB_PATH, help="Database path")):
    """Show all active dunning records."""
    store = DunningStore(db_path)
    records = store.list_all_active()
    if not records:
        console.print("No active dunning records.")
        return
    table = Table(title="Active Dunning Records")
    table.add_column("Subscriber ID")
    table.add_column("Status")
    table.add_column("Billing Issue At")
    table.add_column("Nudges")
    table.add_column("Last Action")
    for r in records:
        table.add_row(
            r.subscriber_id,
            r.status.value,
            r.billing_issue_at.strftime("%Y-%m-%d %H:%M"),
            str(r.nudge_count),
            r.last_action_at.strftime("%Y-%m-%d %H:%M") if r.last_action_at else "-",
        )
    console.print(table)


@app.command()
def stats(db_path: str = typer.Option(DB_PATH, help="Database path")):
    """Show recovery stats."""
    engine = _get_engine(db_path)
    s = engine.get_stats()
    console.print(f"Total issues: {s['total_issues']}")
    console.print(f"Recovered: {s['recovered']}")
    console.print(f"Churned: {s['churned']}")
    console.print(f"Active: {s['active']}")
    console.print(f"Recovery rate: {s['recovery_rate']:.1%}")


@app.command("mark-recovered")
def mark_recovered(
    subscriber_id: str = typer.Argument(..., help="Subscriber ID"),
    db_path: str = typer.Option(DB_PATH, help="Database path"),
):
    """Mark a subscriber as recovered."""
    store = DunningStore(db_path)
    record = store.get(subscriber_id)
    if not record:
        console.print(f"Subscriber {subscriber_id} not found.")
        raise typer.Exit(1)
    store.mark_recovered(subscriber_id)
    console.print(f"Marked {subscriber_id} as recovered.")


@app.command("mark-churned")
def mark_churned(
    subscriber_id: str = typer.Argument(..., help="Subscriber ID"),
    db_path: str = typer.Option(DB_PATH, help="Database path"),
):
    """Mark a subscriber as churned."""
    store = DunningStore(db_path)
    record = store.get(subscriber_id)
    if not record:
        console.print(f"Subscriber {subscriber_id} not found.")
        raise typer.Exit(1)
    store.mark_churned(subscriber_id)
    console.print(f"Marked {subscriber_id} as churned.")


@app.command()
def process(db_path: str = typer.Option(DB_PATH, help="Database path")):
    """Run process_pending() once and show actions taken."""
    engine = _get_engine(db_path)
    actions = engine.process_pending()
    if not actions:
        console.print("No actions taken.")
        return
    for a in actions:
        console.print(f"  {a['subscriber_id']}: {a['action']} -> {a['status']}")


@app.command()
def add(
    subscriber_id: str = typer.Argument(..., help="Subscriber ID"),
    db_path: str = typer.Option(DB_PATH, help="Database path"),
):
    """Manually add a billing issue (for testing)."""
    engine = _get_engine(db_path)
    record = engine.handle_billing_issue(subscriber_id)
    console.print(f"Added billing issue for {subscriber_id} (status: {record.status.value}).")


@app.command()
def analytics(db_path: str = typer.Option(DB_PATH, help="Database path")):
    """Show recovery analytics (rate, avg days, nudge effectiveness)."""
    store = DunningStore(db_path)
    ra = RecoveryAnalytics(store)
    s = ra.summary()
    console.print(f"Recovery rate: {s['recovery_rate']:.1%}")
    console.print(f"Avg days to recovery: {s['avg_days_to_recovery']:.1f}")
    console.print("Nudge effectiveness:")
    ne = s["nudge_effectiveness"]
    if not ne:
        console.print("  No data yet.")
    else:
        for count, rate in ne.items():
            console.print(f"  {count} nudge(s): {rate:.1%}")
