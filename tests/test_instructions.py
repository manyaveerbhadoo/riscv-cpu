import pytest

from asm import assemble
from emulator import Emulator

PROGRAM = "programs/sum.s"


def machine(source, regs=None, mem=None, start=0):
    e = Emulator()
    for i, value in (regs or {}).items():
        e.state.write_reg(i, value)
    for addr, value in (mem or {}).items():
        e.state.store_word(addr, value)
    e.load_program(assemble(source, start), start)
    return e


def expected(before, pc, regs=None, mem=None):
    state = {"pc": pc, "regs": list(before["regs"]), "mem": dict(before["mem"])}
    for i, value in (regs or {}).items():
        state["regs"][i] = value
    for addr, value in (mem or {}).items():
        for k in range(4):
            byte = (value >> (8 * k)) & 0xFF
            if byte:
                state["mem"][addr + k] = byte
            else:
                state["mem"].pop(addr + k, None)
    return state


R_CASES = [
    ("add x3, x1, x2", 5, 7, 12),
    ("add x3, x1, x2", 0xFFFFFFFF, 1, 0),
    ("sub x3, x1, x2", 5, 7, 0xFFFFFFFE),
    ("sub x3, x1, x2", 7, 5, 2),
    ("and x3, x1, x2", 0b1100, 0b1010, 0b1000),
    ("or  x3, x1, x2", 0b1100, 0b1010, 0b1110),
    ("xor x3, x1, x2", 0b1100, 0b1010, 0b0110),
    ("slt x3, x1, x2", 1, 2, 1),
    ("slt x3, x1, x2", 2, 1, 0),
    ("slt x3, x1, x2", 0xFFFFFFFF, 1, 1),
    ("slt x3, x1, x2", 1, 0xFFFFFFFF, 0),
]


@pytest.mark.parametrize("source, rs1, rs2, rd", R_CASES,
                         ids=[f"{s.split()[0]}-{a:#x}-{b:#x}" for s, a, b, _ in R_CASES])
def test_r_type(source, rs1, rs2, rd):
    e = machine(source, regs={1: rs1, 2: rs2})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={3: rd})


I_CASES = [
    ("addi x2, x1, 10", 5, 15),
    ("addi x2, x1, -10", 5, 0xFFFFFFFB),
    ("addi x2, x1, -2048", 0, 0xFFFFF800),
    ("addi x2, x1, 2047", 0, 2047),
    ("slti x2, x1, 5", 4, 1),
    ("slti x2, x1, 5", 5, 0),
    ("slti x2, x1, -1", 0xFFFFFFFE, 1),
    ("slti x2, x1, -3", 0xFFFFFFFE, 0),
    ("ori x2, x1, 0xF", 0xF0, 0xFF),
    ("ori x2, x1, -1", 0, 0xFFFFFFFF),
    ("andi x2, x1, 0xF0", 0xFF, 0xF0),
    ("andi x2, x1, -1", 0xABCD, 0xABCD),
]


@pytest.mark.parametrize("source, rs1, rd", I_CASES,
                         ids=[f"{s.split()[0]}-{s.split(',')[-1].strip()}" for s, _, _ in I_CASES])
def test_i_type(source, rs1, rd):
    e = machine(source, regs={1: rs1})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={2: rd})


def test_lw():
    e = machine("lw x2, 8(x1)", regs={1: 0x100}, mem={0x108: 0xDEADBEEF})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={2: 0xDEADBEEF})


def test_lw_negative_offset():
    e = machine("lw x2, -4(x1)", regs={1: 0x200}, mem={0x1FC: 0x12345678})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={2: 0x12345678})


def test_lw_unwritten_memory_reads_zero():
    e = machine("lw x2, 0(x1)", regs={1: 0x400, 2: 99})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={2: 0})


def test_sw():
    e = machine("sw x2, 4(x1)", regs={1: 0x100, 2: 0xCAFEBABE})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, mem={0x104: 0xCAFEBABE})
    assert [e.state.mem[0x104 + k] for k in range(4)] == [0xBE, 0xBA, 0xFE, 0xCA]


def test_sw_negative_offset():
    e = machine("sw x2, -8(x1)", regs={1: 0x100, 2: 1})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, mem={0xF8: 1})


BRANCH_CASES = [
    ("beq x1, x2, 16", 5, 5, 16),
    ("beq x1, x2, 16", 5, 6, 4),
    ("bne x1, x2, 16", 5, 6, 16),
    ("bne x1, x2, 16", 5, 5, 4),
    ("blt x1, x2, 16", 1, 2, 16),
    ("blt x1, x2, 16", 2, 1, 4),
    ("blt x1, x2, 16", 0xFFFFFFFF, 1, 16),
    ("blt x1, x2, 16", 1, 0xFFFFFFFF, 4),
]


@pytest.mark.parametrize("source, rs1, rs2, pc", BRANCH_CASES,
                         ids=[f"{s.split()[0]}-{a:#x}-{b:#x}" for s, a, b, _ in BRANCH_CASES])
def test_branches(source, rs1, rs2, pc):
    e = machine(source, regs={1: rs1, 2: rs2})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, pc)


def test_branch_backward():
    e = machine("beq x1, x1, 0x10", start=0x20)
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 0x10)


def test_jal():
    e = machine("jal x1, 0x40", start=0x20)
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 0x40, regs={1: 0x24})


def test_jal_to_x0_does_not_link():
    e = machine("jal x0, 0x40", start=0x20)
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 0x40)


def test_jalr():
    e = machine("jalr x1, x2, 4", regs={2: 0x200})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 0x204, regs={1: 4})


def test_jalr_clears_low_bit():
    e = machine("jalr x1, x2, 3", regs={2: 0x200})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 0x202, regs={1: 4})


def test_lui():
    e = machine("lui x1, 0x12345")
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={1: 0x12345000})


def test_lui_max():
    e = machine("lui x1, 0xFFFFF")
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4, regs={1: 0xFFFFF000})


def test_ecall_halts():
    e = machine("ecall")
    before = e.state.dump()
    e.step()
    assert e.state.halted
    assert e.state.dump() == expected(before, 4)


@pytest.mark.parametrize("source", ["addi x0, x1, 5", "add x0, x1, x1", "lui x0, 0x1", "lw x0, 0(x1)"])
def test_writes_to_x0_are_dropped(source):
    e = machine(source, regs={1: 7})
    before = e.state.dump()
    e.step()
    assert e.state.dump() == expected(before, 4)


def test_sum_program_reaches_55():
    e = Emulator()
    e.load_program(assemble(open(PROGRAM).read()))
    e.run()
    assert e.state.read_reg(1) == 55
    assert e.state.halted
