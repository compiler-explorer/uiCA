# JSON Output Format

uiCA can output detailed cycle-by-cycle simulation data using `-json <filename>`. This gives you everything you need to visualize or analyze the pipeline behavior programmatically.

**Important:** To get blocking/stall diagnostics, use `-trackBlocking` along with `-json`. Without this flag, blocking events won't be collected (for performance reasons).

## Overview

The JSON has three top-level sections:

- `parameters` - CPU configuration used for the simulation
- `instructions` - List of instructions that were analyzed
- `cycles` - Array of pipeline events for each cycle

## Parameters

Contains the microarchitecture configuration:

```json
{
  "uArchName": "SKL",
  "issueWidth": 4,
  "IDQWidth": 64,
  "IQWidth": 25,
  "RBWidth": 224,
  "RSWidth": 97,
  "nDecoders": 4,
  "DSBBlockSize": 32,
  "allPorts": ["0", "1", "2", "3", "4", "5", "6", "7"],
  "LSD": false,
  "LSDUnrollCount": 1,
  "mode": "loop",
  "blockingTracked": true
}
```

The queue widths (IDQ, RB, RS) are useful for understanding resource pressure. The `mode` is either "loop" (simulated as a loop) or "unroll" (simulated as straight-line code).

**`blockingTracked`** tells you whether blocking/stall events were collected. If `false`, the absence of `blockedFrom*` events doesn't mean nothing was blocked - it means tracking was disabled for performance.

## Instructions

Each instruction gets an entry with its static properties:

```json
{
  "instrID": 0,
  "asm": "add rax, qword ptr [rsi]",
  "opcode": "480306",
  "source": "DSB",
  "url": "https://www.uops.info/html-instr/ADD_R64_M64.html"
}
```

The `instrID` is used throughout the cycles data to reference this instruction. The `source` tells you where it came from in the front-end: "DSB" (decoded uop cache), "MITE" (legacy decoder), or "MS" (microcode sequencer).

If an instruction has `"macroFusedWithNextInstr": true`, it means it fused with the following instruction (typically cmp/test + jcc).

## Cycles

This is where the action happens. Each cycle contains arrays of pipeline events. The cycle data is sparse - only events that actually happened appear.

### Identifying Uops

Since the code is simulated as a loop, uops are identified hierarchically:

- `instrID` - which instruction (index into the instructions array)
- `rnd` - iteration/round number in the loop
- `lamUopID` - laminated uop index within the instruction (after macro-fusion)
- `fUopID` - fused uop index within the laminated uop (after micro-fusion)
- `uopID` - unfused uop index (the actual execution units see these)

Most simple instructions have a single laminated uop (lamUopID=0) containing one or more fused uops. Memory operations typically unfuse into separate load/store and compute uops.

### Pipeline Events

Here's what can happen each cycle:

**Front-end (instruction fetch/decode):**
- `addedToIQ` - Instructions entering the instruction queue (pre-decode)
- `removedFromIQ` - Instructions leaving the instruction queue
- `addedToIDQ` - Laminated uops entering the decode queue (from MITE, DSB, or MS)
- `removedFromIDQ` - Laminated uops leaving the decode queue

**Out-of-order execution:**
- `addedToRB` - Fused uops entering the reorder buffer (issue stage)
- `addedToRS` - Unfused uops entering the reservation stations
- `readyForDispatch` - Unfused uops whose dependencies are satisfied
- `dispatched` - Unfused uops sent to execution ports
- `executed` - Unfused uops that completed execution
- `removedFromRB` - Fused uops retiring from the reorder buffer

**Blocking/stall diagnostics (requires `-trackBlocking`):**
- `blockedFromDecode` - Instructions that couldn't decode (e.g., IDQ full)
- `blockedFromIssue` - Uops that couldn't issue from renamer (e.g., issue width exceeded, RB/RS full)
- `blockedFromDispatch` - Uops ready but couldn't dispatch to ports (e.g., port busy, resource blocked)

### Understanding Dependencies

The `addedToRS` event includes a `dependsOn` array that shows what this uop is waiting for:

```json
{
  "instrID": 4,
  "rnd": 10,
  "lamUopID": 0,
  "fUopID": 0,
  "uopID": 0,
  "dependsOn": [
    {
      "instrID": 4,
      "rnd": 9,
      "lamUopID": 0,
      "fUopID": 0,
      "uopID": 0
    }
  ]
}
```

This shows a "dec r15" from iteration 10 depending on the same instruction from iteration 9 (register dependency).

### Figuring Out Bottlenecks

To understand why a uop didn't dispatch immediately:

1. Find when it was added to RS (`addedToRS`)
2. Check the `dependsOn` array - if non-empty, it's waiting for those uops to execute
3. Find when it became `readyForDispatch` - this is when all dependencies were satisfied
4. Look for `dispatched` - the gap between ready and dispatched is port contention
5. Check `executed` - the gap from dispatch to execution is the uop latency

Example timeline:
- Cycle 17: `addedToRS` with 1 dependency
- Cycle 24: `readyForDispatch` (dependency satisfied after 7 cycles)
- Cycle 27: `executed` (waited 3 cycles for port availability)

### Blocking Events (with `-trackBlocking`)

When tracking is enabled, you get detailed reasons for stalls:

**`blockedFromDispatch`** entries include a `reason` field:
- `port_busy_older_uop` - Port busy with an older uop (includes `dispatchedInstead` showing which uop got the port)
- `port_blocked_resource` - Port temporarily blocked by resource constraint
- `port_removed_by_constraint` - Uop can't use this port due to constraint

**`blockedFromIssue`** entries include a `reason` field:
- `register_merge_required` - Waiting for register merge uops
- `serializing_instruction_waiting` - Serializing instruction waiting for ROB to drain
- `issue_width_exceeded` - Issue width limit reached
- `reorder_buffer_full` - Reorder buffer full
- `reservation_station_full` - Reservation station full

**`blockedFromDecode`** entries include a `reason` field:
- `idq_full` - Instruction decode queue full (includes current `idqSize`)

These events let you pinpoint exactly why pipeline progress stalled each cycle.

### Dispatched Events

The `dispatched` event is special - it's a dict keyed by port name rather than an array:

```json
{
  "dispatched": {
    "Port1": { "instrID": 3, "rnd": 4, ... },
    "Port2": { "instrID": 0, "rnd": 12, ... },
    "Port6": { "instrID": 1, "rnd": 6, ... }
  }
}
```

This lets you see exactly which execution ports were busy each cycle and what was using them.

## Special Uops

Some entries in `addedToIDQ` or `addedToRS` may have additional boolean flags:

- `"regMergeUop": true` - Register merge uop (related to partial register handling)
- `"stackSyncUop": true` - Stack synchronization uop

These are usually internal implementation details but can show up in the dependencies.

## Example Usage

To visualize a uop's journey through the pipeline, search for its (instrID, rnd) combination across all cycle events. To find bottlenecks, look for large gaps between:
- `addedToRS` and `readyForDispatch` → dependency stalls
- `readyForDispatch` and `dispatched` → port contention
- `addedToIDQ` and `removedFromIDQ` → front-end pressure

The simulation runs for multiple iterations, so comparing the timing across different values of `rnd` can reveal how steady-state performance differs from initial behavior.

---

# Timeline JSON Format (`-timeline`)

uiCA also offers a **uop-oriented timeline format** using `-timeline <filename>`. This format is designed for easier programmatic access to "what happened to uop X in cycle Y" questions, making it simpler to build UIs that display pipeline behavior without requiring deep knowledge of Intel's pipeline internals.

**Important:** Like `-json`, use `-trackBlocking` with `-timeline` to get blocking/stall diagnostics.

## Key Differences from `-json`

The standard `-json` format is **cycle-oriented** (arrays of events per cycle), while `-timeline` is **uop-oriented** (each uop has a sparse event timeline). This makes it easier to:

- Display a table with one row per uop (like the HTML trace output)
- Query "what state is uop X in during cycle Y?"
- Show tooltips explaining why a uop didn't advance
- Avoid needing to understand which pipeline stage an event represents

## Overview

The timeline JSON has four top-level sections:

- `eventCodes` - Legend explaining single-letter event codes
- `parameters` - CPU configuration (same as `-json`)
- `instructions` - List of instructions (same as `-json`)
- `uops` - Array of uops, each with a sparse timeline

## Event Codes

The `eventCodes` section provides a legend for the single-letter codes used in uop timelines:

```json
{
  "P": "Predecoded",
  "Q": "Added to IDQ",
  "I": "Issued",
  "r": "Ready for dispatch",
  "D": "Dispatched",
  "E": "Executed",
  "R": "Retired"
}
```

These represent the major pipeline stages a uop goes through from decode to retirement.

## Uops Structure

Each uop is an object containing:

- Identification: `instrID`, `rnd`, `lamUopID`, `fUopID`, `uopID`
- Port information: `possiblePorts` (array), `actualPort` (string or null)
- Timeline: `events` (dict mapping cycle → event)

```json
{
  "instrID": 0,
  "rnd": 0,
  "lamUopID": 3,
  "fUopID": 0,
  "uopID": 0,
  "possiblePorts": ["0", "1", "5", "6"],
  "actualPort": "5",
  "events": {
    "0": "P",
    "4": {"event": "blocked", "reason": "ms_stalled", "stage": "idq_delivery", "stallType": "pre_stall", "waitingFor": "Q"},
    "5": "Q",
    "6": "I",
    "11": "D",
    "13": "E",
    "36": "R"
  }
}
```

### Reading the Timeline

The `events` dict is **sparse** - only cycles where something happened appear. For most cycles, a single letter indicates the pipeline stage:

- Cycle 0: `"P"` - Uop was predecoded
- Cycle 5: `"Q"` - Uop added to IDQ (decode queue)
- Cycle 6: `"I"` - Uop issued from renamer
- Cycle 11: `"D"` - Uop dispatched to port 5
- Cycle 13: `"E"` - Uop executed
- Cycle 36: `"R"` - Uop retired

Between these events, the uop remains in the previous state (e.g., from cycle 6-10 it's in the "issued" state waiting in the reservation station).

### Blocking Events

When `-trackBlocking` is enabled, cycles where a uop is **blocked** show an object instead of a single letter:

```json
{
  "event": "blocked",
  "stage": "idq_delivery",
  "reason": "ms_stalled",
  "waitingFor": "Q",
  "stallType": "pre_stall"
}
```

The `waitingFor` field tells you which event code this uop is blocked from achieving.

**Common blocking reasons:**

**At decode stage (`waitingFor: "P"`):**
- `ms_post_stall` - Instruction can't decode because microcode sequencer is in cleanup phase

**At IDQ delivery (`waitingFor: "Q"`):**
- `ms_stalled` - Uop waiting in MS queue during stall phase
  - `stallType: "pre_stall"` - MS initializing (switching from MITE to MS)
  - `stallType: "post_stall"` - MS cleaning up (not applicable to IDQ delivery)

**At issue stage (`waitingFor: "I"`):**
- `register_merge_required` - Waiting for register merge uops
- `serializing_instruction_waiting` - Serializing instruction waiting for ROB to drain
- `issue_width_exceeded` - Issue width limit reached
- `reorder_buffer_full` - Reorder buffer full
- `reservation_station_full` - Reservation station full

**At dispatch stage (`waitingFor: "D"`):**
- `port_busy_older_uop` - Port busy with an older uop (includes `port` field)
- `port_blocked_resource` - Port temporarily blocked by resource constraint (includes `port` field)
- `port_removed_by_constraint` - Uop can't use this port due to constraint (includes `port` field)

### Understanding Microcode Sequencer (MS) Behavior

Complex instructions (like `idiv`) are handled by the MS, which generates multiple uops from microcode ROM. The timeline format captures the distinctive stall pattern:

**Example from `idiv eax` (10 uops: 3 MITE + 7 MS):**

**Iteration 0:**
- Cycle 3: First 3 uops (MITE-decoded) get `"Q"` (added to IDQ)
- Cycle 4: MS uops show blocking with `ms_stalled`, `pre_stall` (MS initializing)
- Cycle 5-6: MS delivers uops in batches (`"Q"` events)
- Cycle 7: Next instruction shows blocking with `ms_post_stall` (MS cleanup preventing decode)
- Cycle 8: Normal decoding resumes

This pattern repeats each iteration, creating a characteristic "stutter" in the front-end.

## Comparison with `-json` Format

| Aspect | `-json` (cycle-oriented) | `-timeline` (uop-oriented) |
|--------|-------------------------|---------------------------|
| Structure | Events grouped by cycle | Events grouped by uop |
| Event lookup | "What happened in cycle X?" | "What happened to uop Y?" |
| Blocking info | Separate `blockedFrom*` arrays per cycle | Embedded in uop's event timeline |
| Stage codes | Event names (`addedToIDQ`, `dispatched`, etc.) | Single letters (`P`, `Q`, `I`, `D`, etc.) |
| Use case | Analyzing cycle-by-cycle behavior | Building UI tables, tooltips, timelines |
| File size | Larger (more repetition) | Smaller (sparse representation) |

## Example Usage

**Finding why a uop stalled:**

```python
import json

with open('timeline.json') as f:
    data = json.load(f)

# Find uop 3 from iteration 0
uop = next(u for u in data['uops'] if u['rnd'] == 0 and u['instrID'] == 0 and u['lamUopID'] == 3)

# Check each cycle
for cycle in sorted(uop['events'].keys(), key=int):
    event = uop['events'][cycle]
    if isinstance(event, dict):
        print(f"Cycle {cycle}: BLOCKED - {event['reason']} (waiting for {data['eventCodes'][event['waitingFor']]})")
    else:
        print(f"Cycle {cycle}: {data['eventCodes'][event]}")
```

**Building a table:**

Each uop becomes a table row. The `events` dict provides the sparse data for the timeline cells. When a cell's cycle appears in the events dict, display the event (letter code or tooltip for blocking). Otherwise, show "same state as previous event."

This format makes it straightforward to build interactive visualizations without needing to understand the full complexity of Intel's pipeline architecture.
