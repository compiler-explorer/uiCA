#!/usr/bin/env python3
"""
Convert uiCA timeline JSON output to ASCII pipeline trace.
Usage: uica_ascii.py <timeline.json> [max_iterations]
"""
import json
import sys
from collections import defaultdict

def parse_timeline(json_file):
    with open(json_file) as f:
        return json.load(f)

def format_output(data, max_iterations=None):
    """Format as ASCII with one line per uop, showing instruction on first uop's line."""
    instructions = data['instructions']
    uops = data['uops']

    # Find max instruction length
    max_instr_len = max(len(instr['asm']) for instr in instructions)

    # Filter uops by max_iterations
    filtered_uops = []
    for uop in uops:
        if max_iterations is None or uop['rnd'] < max_iterations:
            filtered_uops.append(uop)

    # Sort by (rnd, instrID, lamUopID) to get uops in order
    sorted_uops = sorted(filtered_uops, key=lambda u: (u['rnd'], u['instrID'], u['lamUopID']))

    # Order preference for display when multiple events in same cycle
    event_order = ['P', 'Q', 'I', 'D', 'E', 'R']

    lines = []
    prev_instr_id = None
    prev_rnd = None

    for uop in sorted_uops:
        instr_id = uop['instrID']
        rnd = uop['rnd']
        lam_uop_id = uop['lamUopID']

        # Build timeline for this uop
        timeline = {}
        for cycle_str, event in uop['events'].items():
            cycle = int(cycle_str)

            # Extract event code (handle blocking objects)
            if isinstance(event, dict):
                # Blocked event - skip for now
                continue
            else:
                event_code = event

            # Skip 'r' (ready for dispatch) to keep it simple
            if event_code == 'r':
                continue

            if cycle not in timeline:
                timeline[cycle] = []
            if event_code not in timeline[cycle]:
                timeline[cycle].append(event_code)

        # Find last cycle with an event for this uop
        last_cycle = max(timeline.keys()) if timeline else 0

        timeline_chars = []
        for cycle in range(last_cycle + 1):
            if cycle in timeline:
                # Sort events by preferred order
                events = sorted(timeline[cycle],
                              key=lambda e: event_order.index(e) if e in event_order else 99)
                timeline_chars.append(''.join(events))
            else:
                timeline_chars.append(' ')

        # Show instruction on first uop's line, blank on subsequent uops
        if instr_id != prev_instr_id or rnd != prev_rnd:
            # First uop of this instruction instance
            instr_asm = instructions[instr_id]['asm']
            padded_instr = instr_asm.ljust(max_instr_len + 1)
        else:
            # Subsequent uop - use blank spaces
            padded_instr = ' ' * (max_instr_len + 1)

        line = f"{padded_instr}|{''.join(timeline_chars)}"
        lines.append(line)

        prev_instr_id = instr_id
        prev_rnd = rnd

    return '\n'.join(lines)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <uica_timeline.json> [max_iterations]", file=sys.stderr)
        sys.exit(1)

    json_file = sys.argv[1]
    max_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else None

    data = parse_timeline(json_file)
    output = format_output(data, max_iterations)
    print(output)

if __name__ == '__main__':
    main()
