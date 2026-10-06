# Design choices

This document explains the current implementation. The [README](README.md)
contains the runnable setup and example. The project models a 19-instruction
RV32I subset in Python, with fixed four-byte instructions and one address space.
It has no cycle timing, pipeline stages, ELF loader, linker, or system calls.
Keeping that boundary makes the state transitions and encodings inspectable.

## State separate from execution

The MachineState class in the state.py file owns the program counter, 32
registers, sparse byte memory, and halt flag. The Emulator class in the
emulator.py file executes instructions against that state. Combining both in
one class would reduce interfaces, but make it harder to construct and inspect
state without execution. Separation adds method calls and requires the emulator
to respect the state object's write methods.

The write_reg method ignores writes to x0 and masks other writes to 32 bits.
Centralizing this rule avoids repeating it in every instruction handler. Its
cost is that directly editing the public regs list can bypass those guarantees.
Registers hold unsigned bit patterns; signed comparisons convert those patterns
when the instruction requires it.

Memory is a dictionary of byte addresses to byte values. Unwritten bytes read
as zero; the store_word and load_word methods assemble words little-endian.
A dense array would have lower per-byte overhead and a clear capacity, but
would require choosing an address-space size and allocating unused storage.
Sparse memory keeps examples small at the cost of dictionary overhead and no
modeled address bounds or alignment traps. Program instructions and data share
that memory, so a store can overwrite code.

The dump method copies registers and returns sorted, nonzero memory entries.
Omitting zero bytes gives equivalent sparse states the same snapshot. Compared
with a raw memory copy, it loses the distinction between unwritten and explicitly
zero bytes. It also excludes the halted attribute: tests check that separately.

## Instruction data and execution logic

The isa.py file defines Instr namedtuple entries with mnemonic, format, opcode,
funct3, funct7, and source syntax. Named fields are clearer than positional
tuples; a dictionary per entry would be more flexible but mutable. The namedtuple
adds a fixed schema and shallow immutability, without a separate class hierarchy.

The INSTRUCTIONS dictionary uses (opcode, funct3, funct7) keys, while the BY_NAME
dictionary serves assembly lookup. A mnemonic-only dictionary would suit the
assembler directly; the tuple index instead exposes encoding distinctions at
the cost of a second index. Both indexes are built from the same entries, and
duplicate encodings or names raise during import. None means a funct field is
absent, which differs from a field fixed to zero.

Encoding format and source operand order are separate metadata. SW is written
with rs2 first and a combined imm(rs1) operand, but its encoded fields are rs1,
rs2, and imm. Recording syntax on the entry avoids mnemonic-specific parser
branches. The cost is another field whose meaning must stay distinct from fmt.

The emulator's step method currently decodes with explicit opcode branches;
it does not consume the instruction table or the assembler's immediate layouts.
Moving execution to table lookup would centralize more metadata, but would
change the existing decoder and require separate validation. Keeping execution
explicit makes each operation easy to trace, at the cost of duplicated encoding
knowledge and possible drift between assembler and emulator.

A three-field lookup alone would not validate ECALL. ECALL and EBREAK differ
at bit 20, outside the key. A match/mask design can specify all fixed bits;
the current decoder instead halts for any word with opcode 0x73. The assembler
emits exactly 0x00000073 for ECALL. Strict SYSTEM validation remains a known
gap, not a property established by the current tests.

## Two assembler passes

The parse function strips comments, records labels, and assigns each Stmt
namedtuple a byte address and source line. Operands become a dictionary keyed
by field name. A positional operand list would be smaller, but would make the
encoder recover source order, especially for stores. Named fields add dictionary
overhead and remain mutable even inside an immutable namedtuple.

The assemble function then resolves B/J targets and calls the encode function.
Forward labels are known because pass 1 has already seen the whole file.
For the sum.s file, the branch at address 12 targets done at 28: the offset is
28 - 12 = 16. JAL at 24 targets loop at 8: the offset is 8 - 24 = -16.

A single pass with fixups could patch unresolved operands later, but would
need another representation and patching mechanism. Two passes retain parsed
statements in memory and assume every instruction occupies four bytes. They
are sufficient here because there is no instruction relaxation or variable
length encoding.

Labels and numeric branch/JAL operands both mean target addresses. Letting a
number mean a relative offset would be convenient for encoding experiments,
but give the same source slot two meanings. One target-to-offset conversion
is easier to trace. Its cost is that absolute numeric targets must be rebased
when moving a program; label-based relative control flow moves naturally.
JALR instead uses a signed immediate added to rs1, then clears the low target bit.

ABI names improve readability without affecting encodings. Supporting numeric
registers only would reduce parser data, but make ordinary assembly examples
less convenient. Identifier labels and integer literals keep parsing small;
the cost is no .L-style labels, arithmetic expressions, or %hi/%lo relocations.

## Encoding and errors

The match function places fixed bits. Format-specific encoder functions add
register fields, while the place_imm function uses the IMM_BITS dictionary to
place immediate slices. Separate hand-written shifts would be more direct per
format, but duplicate the same extraction operation. The shared loop makes
layouts explicit data, at the cost of less obvious bit tracing and the risk of
an incorrect layout row. The decoder retains its own shifts, so this is shared
among encoders, not a single layout source for the whole project.

LUI illustrates the boundary between syntax and encoding: source operand
0x12345 represents the loaded value 0x12345000. The encode_u function converts
the operand before applying the U layout. Keeping the layout in terms of the
loaded immediate gives all rows one interpretation; its cost is that conversion.

Range checks run before bit placement because masking would silently turn an
invalid operand into a different legal bit pattern. B/J offsets must be even.
The encode function checks register ranges for every format; calling a format
encoder directly bypasses that guard. The intended entry point is the assemble
function, or the encode function for an already parsed numeric statement.

The AsmError class subclasses ValueError and carries a source line and message.
Plain error strings would use fewer objects, but force callers to parse text
to recover the location. The CLI formats file:line diagnostics and stops at the
first error; collecting all errors would require continuing with incomplete
parse results. It emits bare hex by default and a listing on request. Raw binary
would need a different output interface. Listing mode parses twice to preserve
the assemble function's simple list-of-words return value.

## Execution and verification

The step method starts with next_pc = pc + 4, overrides it for control flow,
then writes the program counter once. Updating it in each handler would use
fewer local variables but make missing or duplicate increments easier. JAL and
JALR save pc + 4. ECALL advances pc and sets halted; this is an educational halt
convention, not operating-system ECALL behavior. The run method has a step
budget and returns normally if exhausted, so callers must check halted.

Tests combine parameterized cases for shared shapes with individual tests for
different state requirements. One universal case schema would need to model
registers, memory, control flow, and termination; fully individual arithmetic
tests would repeat setup. The hybrid costs two forms of test organization.

Comparing full dumps catches unintended writes that a single-register assertion
misses, at the cost of larger failure diffs. Program tests keep the loaded code
bytes in the expected snapshot and check literal stored bytes separately, so
a paired load/store byte-order error cannot hide behind a successful round trip.
The suite has 53 cases, including five whole programs, and runs in CI on Python
3.12, 3.13, and 3.14. Three jobs cost more than one, but check version compatibility.
CI runs pytest only; adding linting or coverage would add another tool and policy.

The pyproject.toml file configures pytest to import from src. Packaging would
allow imports from any directory, but require changing the current module layout
and invocation. The narrower configuration keeps scripts simple; interactive
API use must run from src or explicitly arrange its import path.

These tests check behavior through this assembler and emulator. They do not
provide independent golden-word coverage of every encoding, a committed
table/decoder consistency check, or full rejection tests for malformed words.
Passing tests demonstrate the checked behaviors, not complete ISA conformance.
