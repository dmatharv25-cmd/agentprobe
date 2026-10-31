"""Runs every attack several times against a fresh agent and prints a reliability report."""
import json
import sys
import time
from rich.console import Console
from rich.table import Table
from agentprobe.agents.tools import ToolBox
from agentprobe.agents.victim import VictimAgent
from agentprobe.attacks.catalog import ATTACKS

# For indirect attacks, the agent must open this note, or the attack never got tested.
EXPOSURE = {
    "indirect-injection-email": "shopping",
    "indirect-injection-leak": "meeting",
}


def make_agent(notes=None, model=None, defended=False):
    if defended:
        from agentprobe.agents.defended import DefendedAgent
        return DefendedAgent(notes=notes, model=model)
    toolbox = ToolBox(notes=notes) if notes else ToolBox()
    return VictimAgent(toolbox=toolbox, model=model) if model else VictimAgent(toolbox=toolbox)


def run_all(model=None, trials=3, defended=False, console=None):
    results = []
    for i, attack in enumerate(ATTACKS, 1):
        r = {"breached": 0, "held": 0, "skipped": 0, "errors": 0, "last_error": ""}
        for t in range(trials):
            if console:
                console.print(f"[dim]attack {i}/{len(ATTACKS)} ({attack.id}), trial {t + 1}/{trials}[/dim]")
            agent = make_agent(attack.notes, model, defended)
            try:
                reply = agent.run(attack.prompt)
            except Exception as e:
                r["errors"] += 1
                r["last_error"] = str(e)
                continue
            if attack.succeeded(reply, agent.toolbox):
                r["breached"] += 1
            elif attack.id in EXPOSURE and EXPOSURE[attack.id] not in agent.toolbox.notes_read:
                r["skipped"] += 1  # agent never read the poisoned note
            else:
                r["held"] += 1
        results.append((attack, r))
    return results


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    defended = len(sys.argv) > 2 and sys.argv[2] == "defended"
    console = Console()

    try:
        make_agent(defended=defended).run("What notes do I have?")
    except Exception as e:
        console.print(f"[red]Preflight failed, the agent can't run:[/red] {e}")
        sys.exit(1)

    results = run_all(trials=trials, defended=defended, console=console)
    label = "defended" if defended else "baseline"
    table = Table(title=f"AgentProbe results: {label} agent ({trials} trials each)")
    for col in ["Attack", "Category", "Breached", "Held", "Not tested", "Errors"]:
        table.add_column(col)
    tb = th = ts = te = 0
    for attack, r in results:
        tb += r["breached"]; th += r["held"]; ts += r["skipped"]; te += r["errors"]
        color = "red" if r["breached"] else "green"
        table.add_row(
            attack.id, attack.category,
            f"[{color}]{r['breached']}[/{color}]", str(r["held"]), str(r["skipped"]), str(r["errors"]),
        )
    console.print(table)

    score = None
    if tb + th == 0:
        console.print("[red]No valid tested runs, so no score.[/red]")
    else:
        score = round(100 * (1 - tb / (tb + th)))
        console.print(
            f"\nReliability score: [bold]{score}/100[/bold] "
            f"({tb} breached of {tb + th} tested runs; {ts} not tested, {te} errors)"
        )
    for _, r in results:
        if r["last_error"]:
            console.print(f"[yellow]error:[/yellow] {r['last_error']}")
            break

    out = {
        "agent": label, "trials": trials, "score": score,
        "breached": tb, "held": th, "not_tested": ts, "errors": te,
        "attacks": [{"id": a.id, "category": a.category, **{k: v for k, v in r.items() if k != "last_error"}} for a, r in results],
    }
    path = f"reports\\{label}_{trials}trials_{int(time.time())}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    console.print(f"Saved: {path}")


if __name__ == "__main__":
    main()
