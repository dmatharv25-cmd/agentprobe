"""Runs every attack against a fresh agent and prints a reliability report."""
import sys
import time
from rich.console import Console
from rich.table import Table
from agentprobe.agents.victim import VictimAgent
from agentprobe.attacks.catalog import ATTACKS


def run_all(model=None, trials=1):
    results = []
    for attack in ATTACKS:
        wins = 0
        for _ in range(trials):
            agent = VictimAgent(model=model) if model else VictimAgent()
            start = time.time()
            try:
                reply = agent.run(attack.prompt)
            except Exception as e:
                reply = f"ERROR: {e}"
            if attack.succeeded(reply, agent.toolbox):
                wins += 1
        results.append((attack, wins, trials, reply))
    return results


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else None
    results = run_all(model=model)
    console = Console()
    table = Table(title="AgentProbe results")
    table.add_column("Attack")
    table.add_column("Category")
    table.add_column("Result")
    breaches = 0
    for attack, wins, trials, _ in results:
        broke = wins > 0
        breaches += broke
        table.add_row(attack.id, attack.category, "[red]BREACHED[/red]" if broke else "[green]held[/green]")
    console.print(table)
    score = round(100 * (1 - breaches / len(results)))
    console.print(f"\nReliability score: [bold]{score}/100[/bold] ({breaches} of {len(results)} attacks succeeded)")


if __name__ == "__main__":
    main()