# RISC-V CPU working instructions

## Start each session

Read the src/state.py and src/emulator.py files before other project work.
Then read the latest sections of the local NOTES.md file, inspect Git status,
and inspect the relevant source and tests. Preserve existing user edits.
Use the current code and Git history to verify progress rather than trusting an
old conversation. If NOTES.md is absent, do not reconstruct private notes from
memory or assume the earlier decisions are known.

## Scope and pace

The scope is a two-pass assembler, a pytest suite for the emulator and assembler,
and GitHub Actions running the suite on every push, plus a README.
Do not design for, build toward, or speculate about later phases.
Work only on the day's agreed task. Keep each session small enough to read and
understand. If it is too large, propose the seam before implementing it.
The user makes design decisions; the agent writes the code.

## Decisions and communication

Before implementing a new design decision, explain the live options, their costs,
and the recommendation with its reasoning. Wait for the user's choice.
Do not reopen decisions already made or offer obviously unsuitable alternatives
just to manufacture a choice. Do not proceed on an unapproved assumption.
After the choice, explain the mechanism so the user could reproduce it from
memory with the code closed.
Whenever mentioning code, state its type explicitly: the encode_r function,
the Emulator class, the dump method, the PROGRAMS constant, the asm.py file.
Put any code shown in a response in a single Markdown code block. Keep design
discussion and review reports outside that block. Do not attach introductory
text, a summary, or post-generation bullet points to the code block itself.

## Coding style

Match the existing naming, formatting, architecture, and Python syntax.
Use minimal, idiomatic code. No unnecessary wrappers, abstraction layers,
defensive boilerplate, placeholders, or TODO stubs.
Use domain names such as imm, funct3, and rd.
Comment only genuinely non-obvious logic. No tutorial comments, banner comments,
decorative separators, emoji, en dashes, or em dashes in code, comments, notes,
or commit messages.
Match existing errors: emulator errors use ValueError and name the offending
field and pc; assembler errors use the AsmError class, a ValueError subclass
carrying the source line. Do not introduce nested try-catch or generic boundaries.

## Locked design decisions

- The MachineState class uses sparse memory keyed by byte address, little-endian.
- The write_reg method is the sole chokepoint for x0 protection and 32-bit masking.
- The dump method returns a copy of the register list and sorted memory keys with
  zero bytes omitted. Compare complete dumps for expected state. It does not
  include the halted attribute, so tests check that attribute separately.
- The step method defaults the next_pc variable to pc + 4, overrides it for
  control flow, and commits the program counter once at the end.
- ECALL, exactly 0x00000073, is the halt instruction, not a zero sentinel.
- Reject unrecognized instructions, including invalid funct3/funct7 combinations.
  Do not silently broaden the accepted instruction set.
- The instruction table is enumerable and exposes each instruction's operand
  shape without requiring the encoder code. Preserve the tuple encoding keys,
  namedtuple entries, and separate surface syntax metadata unless approved.

These are requirements, not proof that every current implementation satisfies
all of them. Report discrepancies and obtain a design decision before changing
behavior beyond the agreed task.

## Structured review

After each function and at least every 20 lines of implementation, answer each
question explicitly outside the code block:

a. Does this duplicate knowledge elsewhere? Name the location and propose
   consolidation if so.
b. What input could produce a silently wrong answer? Handle it or explain why
   it is not handled in this change.
c. Is anything hardcoded that should come from the instruction table?
d. Does malformed or randomly generated input fail loudly and name the fault,
   or fail quietly?
e. Could the user explain every line in an interview? Flag clever constructs.

If an answer is unsatisfying, revise before continuing and report the change.
Before new assembler design work, consult the existing research in NOTES.md.
Verify against primary riscv-opcodes, binutils, Spike, and QEMU sources when
needed. Explain keying, format versus mnemonic organization, and diagnostics
before borrowing a structure. Do not invent a structure without checking.

## Tests and session close

From the repository root, run .venv/Scripts/python -m pytest.
The pyproject.toml file configures pytest to import from the src directory.
Assembly examples and whole-program test inputs live in the programs directory.
Reuse the existing machine and expected functions for tests where appropriate.
Expected results must be independently specified. Whole-program tests compare
full final state and separately assert termination after a bounded run.
Show requested results and structured reviews before committing.
Commit the agreed changes with a factual message, then push. Stage specific
project files. Never add Co-Authored-By, Claude-Session, Generated with Claude Code,
or other assistant attribution trailers to commits or PR descriptions.

## Private study notes

NOTES.md is one local file for the entire project and must never be committed.
Before writing, check that it is neither tracked nor staged. If it is, stop and
tell the user. Never stage it, force-add it, or silently untrack it.
If the file does not exist, first add NOTES.md to .gitignore and commit that
ignore change; only then create the file. An ignore rule does not untrack files.
Append at the end, preserving all earlier content. Never create another notes
file or one file per day. Do not copy private study notes into tracked docs.

For each project session, append this structure, omitting empty subsections:

## Day N: <what was built>
<date>

### Decisions
Options, the user's choice, why, and costs. Include rejected recommendations
and the user's stated reason without inventing one.

### How it works
Mechanism explainable with the code closed. Trace real values step by step.

### Bugs and root causes
What broke and why. Explain silent failures fully.

### IMP
Short, blunt points the user must be able to explain in an interview.

### Reference
Exact values, syntax, encodings, and commands worth retaining.

Cut content that merely restates the code. Follow the same style constraints
as the code. Do not mark an unperformed day's work complete.
