"""Runs every attack several times against a fresh agent and prints a reliability report."""
import sys
from rich.console import Console
from rich.table import Table
from agentprobe.agents.tools import ToolBox
from agentprobe.agents.victim import VictimAgent
from agentprobe.attacks.catalog import ATTACKS


def make_agent(notes=None, model=None):
    toolbox = ToolBox(notes=notes) if notes else ToolBox()
    return VictimAgent(toolbox=toolbox, model=model) if model else VictimAgent(toolbox=toolbox)


def run_all(model=None, trials=3):
    results = []
    for attack in ATTACKS:
        wins = errors = 0
        last_error = ""
        for _ in range(trials):
            agent = make_agent(attack.notes, model)
            try:
                reply = agent.run(attack.prompt)
            except Exception as e:
                errors += 1
                last_error = str(e)
                continue  # errors are not counted as "held"
            if attack.succeeded(reply, agent.toolbox):
                wins += 1
        results.append((attack, wins, errors, trials, last_error))
    return results


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    console = Console()

    # Preflight: stop early if the model or server is broken.
    try:
        make_agent().run("What notes do I have?")
    except Exception as e:
        console.print(f"[red]Preflight failed, the agent can't run:[/red] {e}")
        sys.exit(1)

    results = run_all(trials=trials)
    table = Table(title=f"AgentProbe results ({trials} trials each)")
    table.add_column("Attack")
    table.add_column("Category")
    table.add_column("Breach rate")
    table.add_column("Errors")
    total_wins = total_valid = total_errors = 0
    for attack, wins, errors, n, last_error in results:
        valid = n - errors
        total_wins += wins
        total_valid += valid
        total_errors += errors
        color = "red" if wins else "green"
        table.add_row(attack.id, attack.category, f"[{color}]{wins}/{valid}[/{color}]", str(errors))
    console.print(table)
    if total_valid == 0:
        console.print("[red]No valid runs, so no score. Check the errors above.[/red]")
        return
    score = round(100 * (1 - total_wins / total_valid))
    console.print(f"\nReliability score: [bold]{score}/100[/bold] ({total_wins} of {total_valid} valid runs breached, {total_errors} errors)")
    for attack, wins, errors, n, last_error in results:
        if last_error:
            console.print(f"[yellow]{attack.id} error:[/yellow] {last_error}")
            break


if __name__ == "__main__":
    main()