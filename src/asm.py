from collections import namedtuple

from isa import BY_NAME, FORMATS

ABI = ("zero ra sp gp tp t0 t1 t2 s0 s1 a0 a1 a2 a3 a4 a5 a6 a7 "
       "s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 t3 t4 t5 t6").split()

REGS = {f"x{n}": n for n in range(32)}
REGS.update({name: n for n, name in enumerate(ABI)})
REGS["fp"] = 8

Stmt = namedtuple("Stmt", "name operands addr lineno")


class AsmError(ValueError):
    def __init__(self, lineno, msg):
        super().__init__(f"line {lineno}: {msg}")
        self.lineno = lineno
        self.msg = msg


def parse_reg(tok, lineno):
    if not tok:
        raise AsmError(lineno, "missing register")
    if tok not in REGS:
        raise AsmError(lineno, f"unknown register {tok!r}")
    return REGS[tok]


def parse_imm(tok, lineno):
    if not tok:
        raise AsmError(lineno, "missing immediate")
    if tok.isidentifier():
        return tok
    try:
        return int(tok, 0)
    except ValueError:
        raise AsmError(lineno, f"bad immediate {tok!r}")


def parse_stmt(line, addr, lineno):
    parts = line.split(None, 1)
    name = parts[0]
    if name not in BY_NAME:
        raise AsmError(lineno, f"unknown mnemonic {name!r}")

    entry = BY_NAME[name]
    arg_text = parts[1] if len(parts) > 1 else ""
    toks = [t.strip() for t in arg_text.split(",")] if arg_text else []
    want = ", ".join(entry.syntax)
    if toks and not toks[-1]:
        raise AsmError(lineno, f"trailing comma in {name} operands ({want})")
    if not all(toks):
        raise AsmError(lineno, f"missing operand in {name} ({want})")
    if len(toks) != len(entry.syntax):
        raise AsmError(
            lineno,
            f"{name} takes {len(entry.syntax)} operands ({want}), "
            f"got {len(toks)}: {arg_text.strip()!r}"
        )

    operands = {}
    for slot, tok in zip(entry.syntax, toks):
        if slot == "imm(rs1)":
            imm, sep, rs1 = tok.partition("(")
            if not sep or not rs1.endswith(")"):
                raise AsmError(lineno, f"expected imm(rs1) for {name}, got {tok!r}")
            operands["imm"] = parse_imm(imm.strip(), lineno)
            operands["rs1"] = parse_reg(rs1[:-1].strip(), lineno)
        elif slot == "imm":
            operands["imm"] = parse_imm(tok, lineno)
        elif slot in ("rd", "rs1", "rs2"):
            operands[slot] = parse_reg(tok, lineno)
        else:
            raise AsmError(lineno, f"unknown operand slot {slot!r} for {name}")
    return Stmt(name, operands, addr, lineno)


def parse(text, start=0):
    stmts = []
    labels = {}
    addr = start
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.split("#")[0].strip()
        while ":" in line:
            label, line = line.split(":", 1)
            label, line = label.strip(), line.strip()
            if not label.isidentifier():
                raise AsmError(lineno, f"bad label {label!r}")
            if label in labels:
                raise AsmError(lineno, f"duplicate label {label!r}")
            labels[label] = addr
        if not line:
            continue
        stmts.append(parse_stmt(line, addr, lineno))
        addr += 4
    return stmts, labels


def match(entry):
    word = entry.opcode
    if entry.funct3 is not None:
        word |= entry.funct3 << 12
    if entry.funct7 is not None:
        word |= entry.funct7 << 25
    return word


def encode_r(stmt, entry):
    ops = stmt.operands
    return match(entry) | ops["rd"] << 7 | ops["rs1"] << 15 | ops["rs2"] << 20


# (word_hi, word_lo, imm_lo) for each slice of the immediate
IMM_BITS = {
    "I": [(31, 20, 0)],
    "S": [(31, 25, 5), (11, 7, 0)],
    "B": [(31, 31, 12), (30, 25, 5), (11, 8, 1), (7, 7, 11)],
    "U": [(31, 12, 12)],
    "J": [(31, 31, 20), (30, 21, 1), (20, 20, 11), (19, 12, 12)],
}


def place_imm(imm, fmt):
    word = 0
    for hi, lo, imm_lo in IMM_BITS[fmt]:
        mask = (1 << (hi - lo + 1)) - 1
        word |= ((imm >> imm_lo) & mask) << lo
    return word


def check_imm(stmt, min_val, max_val, must_be_even=False):
    imm = stmt.operands["imm"]
    if isinstance(imm, str):
        raise AsmError(stmt.lineno, f"label {imm!r} not supported as {stmt.name} imm")
    if not min_val <= imm <= max_val:
        raise AsmError(stmt.lineno, f"imm {imm} out of range [{min_val}, {max_val}] for {stmt.name}")
    if must_be_even and imm % 2:
        raise AsmError(stmt.lineno, f"imm {imm} must be even for {stmt.name}")


def encode_i(stmt, entry):
    ops = stmt.operands
    check_imm(stmt, -2048, 2047)
    return match(entry) | ops["rd"] << 7 | ops["rs1"] << 15 | place_imm(ops["imm"], entry.fmt)


def encode_s(stmt, entry):
    ops = stmt.operands
    check_imm(stmt, -2048, 2047)
    return match(entry) | ops["rs1"] << 15 | ops["rs2"] << 20 | place_imm(ops["imm"], entry.fmt)


def encode_b(stmt, entry):
    ops = stmt.operands
    check_imm(stmt, -4096, 4094, must_be_even=True)
    return match(entry) | ops["rs1"] << 15 | ops["rs2"] << 20 | place_imm(ops["imm"], entry.fmt)


# lui is written with the 20-bit operand, IMM_BITS places the value it loads
def encode_u(stmt, entry):
    ops = stmt.operands
    check_imm(stmt, 0, 0xFFFFF)
    return match(entry) | ops["rd"] << 7 | place_imm(ops["imm"] << 12, entry.fmt)


def encode_j(stmt, entry):
    ops = stmt.operands
    check_imm(stmt, -1048576, 1048574, must_be_even=True)
    return match(entry) | ops["rd"] << 7 | place_imm(ops["imm"], entry.fmt)


def encode_sys(stmt, entry):
    return match(entry)


ENCODERS = {
    "R": encode_r, "I": encode_i, "S": encode_s, "B": encode_b,
    "U": encode_u, "J": encode_j, "SYS": encode_sys,
}


def encode(stmt):
    entry = BY_NAME[stmt.name]
    if entry.fmt not in ENCODERS:
        raise AsmError(stmt.lineno, f"no encoder for format {entry.fmt} ({stmt.name})")
    for slot in FORMATS[entry.fmt]:
        if slot != "imm" and not 0 <= stmt.operands[slot] <= 31:
            raise AsmError(stmt.lineno, f"{slot} {stmt.operands[slot]} out of range [0, 31]")
    return ENCODERS[entry.fmt](stmt, entry)


def assemble(text, start=0):
    stmts, labels = parse(text, start)
    words = []
    for stmt in stmts:
        if BY_NAME[stmt.name].fmt in ("B", "J"):
            # a number is a target address too, same as a label
            target = stmt.operands["imm"]
            if isinstance(target, str):
                if target not in labels:
                    raise AsmError(stmt.lineno, f"undefined label {target!r}")
                target = labels[target]
            stmt = stmt._replace(operands=dict(stmt.operands, imm=target - stmt.addr))
        words.append(encode(stmt))
    return words


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="assemble RV32I source to machine code")
    ap.add_argument("source")
    ap.add_argument("--listing", action="store_true",
                    help="print address, word and source line instead of bare hex")
    args = ap.parse_args()

    try:
        text = open(args.source).read()
    except OSError as err:
        sys.exit(f"{args.source}: error: {err.strerror}")

    lines = text.splitlines()
    try:
        words = assemble(text)
    except AsmError as err:
        print(f"{args.source}:{err.lineno}: error: {err.msg}", file=sys.stderr)
        if 1 <= err.lineno <= len(lines):
            print(f"  {lines[err.lineno - 1].strip()}", file=sys.stderr)
        sys.exit(1)

    if args.listing:
        stmts, _ = parse(text)
        for stmt, word in zip(stmts, words):
            print(f"0x{stmt.addr:04x}  {word:08x}  {lines[stmt.lineno - 1].strip()}")
    else:
        for word in words:
            print(f"{word:08x}")
