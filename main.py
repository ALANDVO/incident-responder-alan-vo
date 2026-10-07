#!/usr/bin/env python3
# incident-responder — AI incident response copilot that takes incident logs or a timeline, classifies severity, identifies blast radius, suggests containment steps, and generates comms templates for status pages, Slack, and email.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
def _load_incident(args):
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    with open(args.file) as f:
        content = f.read()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return "\n".join(json.dumps(e) for e in data)
        return json.dumps(data, indent=2)
    except json.JSONDecodeError:
        return content

def triage(args):
    """Classify severity and suggest immediate containment."""
    llm = LLM()
    incident = _load_incident(args)
    print(f"Triage: {len(incident.split())} tokens of incident data\n")

    severity = llm.classify(
        text=incident[:6000],
        categories=["SEV1", "SEV2", "SEV3", "SEV4"],
        instructions="Classify incident severity. SEV1 = total outage or data loss affecting all customers. SEV2 = major feature down or >25% of users affected. SEV3 = degraded performance or <25% users. SEV4 = minor issue, internal only. Consider: user impact, data loss risk, revenue impact, duration."
    )
    sev = severity.get("category", "SEV3")
    icons = {"SEV1": "🔴", "SEV2": "🟠", "SEV3": "🟡", "SEV4": "🔵"}
    print(f"  Severity: {icons.get(sev, '⚪')} {sev}")
    print(f"  Confidence: {severity.get('confidence', '?')}")
    print(f"  Reasoning: {severity.get('reasoning', '')}\n")

    containment = llm.generate(
        f"Incident data:\n{incident[:6000]}\n\n"
        f"Severity: {sev}\n\n"
        "Produce an immediate containment plan. For each step: action, owner role (IC/SRE/DBA/Platform), estimated time, risk if wrong, reversibility. "
        "Order by: fastest to execute first, highest impact first. Max 8 steps. "
        "Also identify: what to STOP doing (stop deploys? stop migrations?), what to ROLL BACK, and what to SCALE.",
        system="You are the incident commander making the first 10 minutes' decisions. Containment before root cause. Every step must be executable by a human within 5 minutes."
    )
    print(f"{'='*60}\nCONTAINMENT PLAN\n{'='*60}\n{containment}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"severity": sev, "confidence": severity.get("confidence"), "reasoning": severity.get("reasoning"), "containment": containment, "triaged_at": datetime.now().isoformat()}, f, indent=2)
        print(f"\nSaved to {args.output}")
    return sev

def blast(args):
    """Analyze blast radius and affected scope."""
    llm = LLM()
    incident = _load_incident(args)
    services = (args.services or "").split(",")
    print(f"Blast radius analysis (services: {services or 'auto-detect'})\n")

    result = llm.generate(
        f"Incident data:\n{incident[:6000]}\n\n"
        f"Known services in scope: {services or 'auto-detect from logs'}\n\n"
        "Analyze the blast radius. Produce:\n"
        "1. AFFECTED SERVICES: list each with: what is broken, how many users affected (estimate), since when\n"
        "2. DATA IMPACT: any data loss, corruption, or at-risk data\n"
        "3. DEPENDENCY CHAIN: which downstream/upstream services are impacted and how\n"
        "4. USER IMPACT: which user segments (free/paid/enterprise), which regions, estimated count\n"
        "5. RECOVERY ESTIMATE: realistic TTR based on what is needed\n\n"
        "Be specific with numbers where the data supports it. Mark estimates as ESTIMATED.",
        system="You are an SRE mapping incident impact. Precision over pessimism — but never understate data loss risk."
    )
    print(result)

    if args.output:
        with open(args.output, "w") as f:
            f.write(f"# Blast Radius Analysis\n\n{result}\n")
        print(f"\nSaved to {args.output}")
    return result

def comms(args):
    """Generate comms templates for the incident."""
    llm = LLM()
    incident = _load_incident(args)
    phase = args.phase or "initial"
    channel = args.channel or "status"
    print(f"Generating {channel} comms ({phase} phase)...\n")

    templates = {
        "status": {
            "initial": "Write the initial status page update. Format: 'We are investigating an issue affecting [service]. Impact: [what users experience]. We will update every 30 minutes. Last update: [time].' Keep it under 3 sentences. No internal jargon. Acknowledge the issue without admitting fault.",
            "update": "Write an in-progress status page update. Include: what has been identified, what has been done, what is next, current user impact. 3-5 sentences. Professional, transparent, no blame.",
            "resolved": "Write the resolution status page update. Include: what happened (1 sentence), when it started and ended, what was done to fix it, what we're doing to prevent recurrence. 4-6 sentences. Grateful and forward-looking.",
        },
        "slack": {
            "initial": "Write a Slack #inc-channel update. Start with 🚨 + one-line summary. Then: *Impact*, *Current state*, *Next steps* (3 bullets), *Who's doing what*. Max 12 lines. Engineers will read this on their phone.",
            "exec": "Write an exec summary for leadership. 5 sentences max. What happened, user impact (numbers if known), revenue impact estimate, current status, what we need from them. No technical detail they do not need.",
            "resolved": "Write the Slack resolution update. ✅ + what was fixed, duration, user impact summary, link to postmortem (placeholder). 4-6 lines. Thank the IC team by role.",
        },
        "email": {
            "customer": "Write a customer-facing email. Subject line + body. Formal but human. What happened, impact on their account, what we have done, what is next. Include a direct contact link. 150-250 words.",
            "leadership": "Write a leadership email. Subject + body. Situation, impact (revenue + users), actions taken, actions needed, expected resolution. Include a 3-bullet 'What we need' section. 200-300 words.",
            "engineering": "Write an engineering all-hands email. What happened (technical, 3 sentences), what was learned, what is changing in our processes. No blame. 150-200 words.",
        },
    }

    instruction = templates.get(channel, {}).get(phase, templates["status"]["initial"])

    output = llm.generate(
        f"Incident data:\n{incident[:4000]}\n\n{instruction}\n\n"
        "Use only facts present in the incident data. Where specifics are missing, use [BRACKETED PLACEHOLDER]. Do not invent service names, user counts, or timestamps not in the data.",
        system="You write incident communications. Clear, calm, factual. Never blame individuals. Never overpromise. Every sentence must be defensible in a postmortem."
    )

    print(f"{'='*60}")
    print(f"{channel.upper()} — {phase.upper()}")
    print(f"{'='*60}")
    print(output)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nSaved to {args.output}")
    return output

def postmortem(args):
    """Generate a postmortem skeleton from incident data."""
    llm = LLM()
    incident = _load_incident(args)
    print("Generating postmortem skeleton...\n")

    result = llm.generate(
        f"Incident data:\n{incident[:6000]}\n\n"
        "Generate a post-incident review document with these sections:\n"
        "## Summary (5 sentences: what, when, impact, root cause, resolution)\n"
        "## Timeline (table: | Time | Event | Detector |) — reconstruct from the data\n"
        "## Root Cause Analysis (5-Why chain if data supports it, otherwise hypothesis)\n"
        "## What Went Well (specific, credited to teams/roles)\n"
        "## What Went Poorly (specific, no blame)\n"
        "## Contributing Factors (systemic, not individual)\n"
        "## Action Items (table: | # | Action | Owner | Due | Priority |) — 4-8 items\n"
        "## Lessons Learned (3-5 actionable takeaways)\n\n"
        "Mark anything not supported by the data as [TO BE VERIFIED]. Do not fabricate timeline entries.",
        system="You write blameless postmortems. Focus on systems and processes, not people. Every action item must be concrete and assignable."
    )
    print(result)

    if args.output:
        with open(args.output, "w") as f:
            f.write(f"# Post-Incident Review\n\n**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n{result}\n")
        print(f"\nSaved to {args.output}")
    return result

def main():
    import argparse
    p = argparse.ArgumentParser(prog="incident-responder", description="AI incident response copilot")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("triage", help="Classify severity + containment plan")
    t.add_argument("--file", default=None); t.add_argument("--stdin", action="store_true"); t.add_argument("--output", default=None)
    t.set_defaults(fn=triage)

    b = sub.add_parser("blast", help="Blast radius analysis")
    b.add_argument("--file", default=None); b.add_argument("--stdin", action="store_true")
    b.add_argument("--services", default=None); b.add_argument("--output", default=None)
    b.set_defaults(fn=blast)

    c = sub.add_parser("comms", help="Generate comms templates")
    c.add_argument("--file", default=None); c.add_argument("--stdin", action="store_true")
    c.add_argument("--channel", choices=["status", "slack", "email"], default="status")
    c.add_argument("--phase", choices=["initial", "update", "resolved", "exec", "customer", "leadership", "engineering"], default="initial")
    c.add_argument("--output", default=None)
    c.set_defaults(fn=comms)

    pm = sub.add_parser("postmortem", help="Generate postmortem skeleton")
    pm.add_argument("--file", default=None); pm.add_argument("--stdin", action="store_true"); pm.add_argument("--output", default=None)
    pm.set_defaults(fn=postmortem)

    args = p.parse_args()
    if not args.file and not getattr(args, "stdin", False):
        p.error("provide --file or --stdin")
    args.fn(args)

if __name__ == '__main__':
    main()
