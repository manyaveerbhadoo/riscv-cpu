# RISC-V assembler and emulator

A small Python implementation of a 19-instruction RV32I subset. It assembles
text into 32-bit instruction words and executes them with 32 registers and
little-endian memory. It is an instruction-level learning project: there is no
hardware pipeline, operating system, or complete RV32I implementation.

## Setup

Install Git and Python 3.12, 3.13, or 3.14. Verify `git --version` and
`python --version` first. If `python` is unavailable, use your Python launcher's
command or the full path to your installed Python executable for the venv command.

Run these commands in PowerShell from the directory where you want the clone:

```powershell
git clone https://github.com/manyaveerbhadoo/riscv-cpu.git
cd riscv-cpu
python -m venv .venv
.venv/Scripts/python -m pip install pytest==9.1.1
```

On Linux/macOS, use `python3` to create the venv and replace `Scripts/python`
with `bin/python` in every command below. No activation or package installation
of this repository is needed. The assembler and emulator use only the standard
library; pytest is needed for tests.

## Assemble a program

From the repository root:

```powershell
.venv/Scripts/python src/asm.py programs/sum.s
.venv/Scripts/python src/asm.py --listing programs/sum.s
```

The first command prints eight hexadecimal words, one per line. The second
adds addresses and source lines. Assembly errors go to stderr with the filename,
line number, and offending line, and exit with status 1.

## Worked example: assembly in, registers out

The [sum.s file](programs/sum.s) sums 1 through 10:

```asm
        addi x1, x0, 0
        addi x2, x0, 1
loop:   addi x3, x0, 11
        beq  x2, x3, done
        add  x1, x1, x2
        addi x2, x2, 1
        jal  x0, loop
done:   ecall
```

The emulator has a Python API. To run this actual file, start an interactive
Python session from the src directory, where its modules are importable:

```powershell
cd src
../.venv/Scripts/python
```

At the `>>>` prompt, paste:

```python
from pathlib import Path
from asm import assemble
from emulator import Emulator
e = Emulator()
e.load_program(assemble(Path("../programs/sum.s").read_text()))
e.run(max_steps=100)
assert e.state.halted, "sum.s did not halt within 100 steps"
print({"pc": e.state.pc, "halted": e.state.halted})
print(e.state.regs)
exit()
```

Expected output before exiting Python:

```text
{'pc': 32, 'halted': True}
[0, 55, 11, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

x1 accumulates the sum; x2 reaches 11 and matches x3. ECALL at address 28
halts after advancing the program counter to 32. All other registers stay zero.
The run method returns when its limit expires too, so check the halted attribute.
The dump method returns pc, all registers, and nonzero memory bytes for inspection.

Return to the repository root:

```powershell
cd ..
.venv/Scripts/python src/emulator.py
```

That last command prints `55` from a built-in machine-code demonstration. It
does not read an assembly file or accept the assembler's output on stdin.

## Tests

From the repository root:

```powershell
.venv/Scripts/python -m pytest
.venv/Scripts/python -m pytest -q -k program
```

Expect 53 passing tests in the full suite and five in the program-only selection.
Tests cover every supported instruction and five complete programs, comparing
full machine state and checking termination separately. The pyproject.toml file
configures imports and discovery. GitHub Actions runs the suite on Python 3.12,
3.13, and 3.14 for pushes and pull requests.

## Architecture and supported syntax

The isa.py file defines instruction metadata; the asm.py file parses and encodes
in two passes so forward labels work. The state.py file owns registers and
memory; the emulator.py file decodes and executes one instruction per step.
Separate state makes snapshots testable independently of execution. Read
[DESIGN.md](DESIGN.md) for the alternatives, costs, and current limitations.

Supported instructions: `add sub slt xor or and`, `addi slti ori andi`,
`lw sw`, `beq bne blt`, `jal jalr lui ecall`. Use lowercase mnemonics,
x0 through x31 or ABI names, `#` comments, and identifier labels. There are no
directives, pseudoinstructions, or relocation expressions. Loads/stores use
`lw rd, imm(rs1)` / `sw rs2, imm(rs1)`; JALR uses `jalr rd, rs1, imm`.
Branch and JAL numeric operands are absolute target addresses, just like labels.
LUI takes a 20-bit operand. ECALL is this project's halt convention.
