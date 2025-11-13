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
    """Format as ASCII with instruction | event timeline."""
    instructions = data['instructions']
    uops = data['uops']

    # Find max instruction length
    max_instr_len = max(len(instr['asm']) for instr in instructions)

    # Find max cycle and iteration
    max_cycle = 0
    max_rnd = 0
    for uop in uops:
        max_rnd = max(max_rnd, uop['rnd'])
        # Only consider cycles from uops we'll actually show
        if max_iterations is None or uop['rnd'] < max_iterations:
            if uop['events']:
                max_cycle = max(max_cycle, max(int(c) for c in uop['events'].keys()))

    # Limit iterations if requested
    if max_iterations is not None:
        max_rnd = min(max_rnd, max_iterations - 1)

    # Group uops by (instrID, rnd) - we want one line per instruction instance
    # Since instructions can have multiple uops, we need to merge their events
    instr_timelines = defaultdict(lambda: {})  # (instrID, rnd) -> {cycle: [events]}

    for uop in uops:
        if max_iterations is not None and uop['rnd'] >= max_iterations:
            continue

        key = (uop['instrID'], uop['rnd'])
        for cycle_str, event in uop['events'].items():
            cycle = int(cycle_str)
            if cycle not in instr_timelines[key]:
                instr_timelines[key][cycle] = []

            # Extract event code (handle blocking objects)
            if isinstance(event, dict):
                # Blocked event - skip for now (could show 'b' or similar)
                continue
            else:
                event_code = event

            # Skip 'r' (ready for dispatch) to keep it simple
            if event_code == 'r':
                continue

            # Avoid duplicates in the same cycle
            if event_code not in instr_timelines[key][cycle]:
                instr_timelines[key][cycle].append(event_code)

    # Sort by (rnd, instrID) for output
    sorted_keys = sorted(instr_timelines.keys(), key=lambda x: (x[1], x[0]))

    lines = []
    for instr_id, rnd in sorted_keys:
        timeline = instr_timelines[(instr_id, rnd)]

        # Get instruction assembly
        instr_asm = instructions[instr_id]['asm']

        # Build timeline string with events in order Q I D E R etc.
        # Order preference for display when multiple events in same cycle
        event_order = ['P', 'Q', 'I', 'D', 'E', 'R']

        # Find last cycle with an event for this instruction
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

        # Format line
        padded_instr = instr_asm.ljust(max_instr_len + 1)
        line = f"{padded_instr}|{''.join(timeline_chars)}"
        lines.append(line)

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
