import sys
from agentprobe.attacks.catalog import ATTACKS
from agentprobe.runner import make_agent

ids = sys.argv[1:] or ["indirect-injection-email", "indirect-injection-leak", "leak-direct"]
for attack in ATTACKS:
    if attack.id not in ids:
        continue
    agent = make_agent(attack.notes)
    reply = agent.run(attack.prompt)
    print(f"\n=== {attack.id} ===")
    print("TOOL CALLS:", [c[0] + str(c[1]) for c in agent.toolbox.call_log])
    print("EMAILS:", agent.toolbox.outbox)
    print("REPLY:", reply)
    print("BREACHED:", attack.succeeded(reply, agent.toolbox))