from collections import namedtuple

# funct3 and funct7 are None when the field is not part of the encoding,
# which is not the same as the field being zero.
Instr = namedtuple("Instr", "name fmt opcode funct3 funct7", defaults=(None, None))

# SYS takes no operands, so every bit outside opcode/funct3/funct7 is a fixed zero.
FORMATS = {
    "R": ("rd", "rs1", "rs2"),
    "I": ("rd", "rs1", "imm"),
    "S": ("rs1", "rs2", "imm"),
    "B": ("rs1", "rs2", "imm"),
    "U": ("rd", "imm"),
    "J": ("rd", "imm"),
    "SYS": (),
}

_INSTRS = [
    Instr("add",   "R",   0x33, 0x0, 0x00),
    Instr("sub",   "R",   0x33, 0x0, 0x20),
    Instr("slt",   "R",   0x33, 0x2, 0x00),
    Instr("xor",   "R",   0x33, 0x4, 0x00),
    Instr("or",    "R",   0x33, 0x6, 0x00),
    Instr("and",   "R",   0x33, 0x7, 0x00),

    Instr("addi",  "I",   0x13, 0x0),
    Instr("slti",  "I",   0x13, 0x2),
    Instr("ori",   "I",   0x13, 0x6),
    Instr("andi",  "I",   0x13, 0x7),

    Instr("lw",    "I",   0x03, 0x2),
    Instr("jalr",  "I",   0x67, 0x0),
    Instr("sw",    "S",   0x23, 0x2),

    Instr("beq",   "B",   0x63, 0x0),
    Instr("bne",   "B",   0x63, 0x1),
    Instr("blt",   "B",   0x63, 0x4),

    Instr("jal",   "J",   0x6F),
    Instr("lui",   "U",   0x37),
    Instr("ecall", "SYS", 0x73, 0x0, 0x00),
]

INSTRUCTIONS = {}
for entry in _INSTRS:
    if entry.fmt not in FORMATS:
        raise ValueError(f"unknown format {entry.fmt} for {entry.name}")
    key = (entry.opcode, entry.funct3, entry.funct7)
    if key in INSTRUCTIONS:
        raise ValueError(f"duplicate encoding for {entry.name}: already used by {INSTRUCTIONS[key].name}")
    INSTRUCTIONS[key] = entry
