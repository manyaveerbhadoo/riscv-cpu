from state import MachineState


def to_signed(value):
    if (value >> 31) & 1:
        return value - 0x100000000
    return value

def sign_extend(value, bits):
    if (value >> (bits-1)) & 1:
        return value - (1 << bits)
    return value



class Emulator:
    def __init__(self, state=None):
        self.state = state if state is not None else MachineState()

    
    def step(self):
        instr = self.state.load_word(self.state.pc)
        next_pc = self.state.pc + 4
        opcode = instr & 0x7F
        if opcode == 0x33:
            rd = (instr >> 7) & 0x1F
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            rs2 = (instr >> 20) & 0x1F
            funct7 = (instr >> 25) & 0x7F
            
            val1 = self.state.read_reg(rs1)
            val2 = self.state.read_reg(rs2)
            if funct3 == 0x0:
                if funct7 == 0x00:
                    result = val1 + val2      # add
                elif funct7 == 0x20:
                    result = val1 - val2      # sub
                else:
                    raise ValueError(f"unsupported funct7: {funct7:#x} at pc={self.state.pc:#x}")
            
            elif funct3 == 0x7 and funct7 == 0x00:
                result = val1 & val2
            elif funct3 == 0x6 and funct7 == 0x00:
                result = val1 | val2
            elif funct3 == 0x4 and funct7 == 0x00:
                result = val1 ^ val2
            elif funct3 == 0x2 and funct7 == 0x00:
                result = 1 if to_signed(val1) < to_signed(val2) else 0
            
            else:
                raise ValueError(
                    f"unsupported R-type: funct3={funct3:#x} funct7={funct7:#x} "
                    f"at pc={self.state.pc:#x}"
                )

            self.state.write_reg(rd, result)

        elif opcode == 0x13:
            rd = (instr >> 7) & 0x1F
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            imm = (instr >> 20) & 0xFFF
            imm = sign_extend(imm, 12)

            val1 = self.state.read_reg(rs1)

            if funct3 == 0x0:
                result = val1 + imm                    # addi
            elif funct3 == 0x2:
                result = 1 if to_signed(val1) < imm else 0    # slti
            elif funct3 == 0x6:
                result = val1 | imm                    # ori
            elif funct3 == 0x7:
                result = val1 & imm                    # andi
            else:
                raise ValueError(f"unsupported I-type funct3: {funct3:#x} at pc={self.state.pc:#x}")

            self.state.write_reg(rd, result)

        elif opcode == 0x73:
            self.state.halted = True

        elif opcode == 0x03:
            rd = (instr >> 7) & 0x1F
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            imm = sign_extend((instr >> 20) & 0xFFF, 12)

            val1 = self.state.read_reg(rs1)
            addr = val1 + imm

            if funct3 == 0x2:
                result = self.state.load_word(addr)
            else:
                raise ValueError(f"unsupported load funct3: {funct3:#x} at pc={self.state.pc:#x}")

            self.state.write_reg(rd, result)

        elif opcode == 0x23:
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            rs2 = (instr >> 20) & 0x1F

            imm_low = (instr >> 7) & 0x1F
            imm_high = (instr >> 25) & 0x7F
            imm = sign_extend((imm_high << 5) | imm_low, 12)

            addr = self.state.read_reg(rs1) + imm
            value = self.state.read_reg(rs2)

            if funct3 == 0x2:
                self.state.store_word(addr, value)
            else:
                raise ValueError(f"unsupported store funct3: {funct3:#x} at pc={self.state.pc:#x}")

        elif opcode == 0x63:
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            rs2 = (instr >> 20) & 0x1F

            imm_11   = (instr >> 7)  & 0x1      # bit 7      → imm[11]
            imm_4_1  = (instr >> 8)  & 0xF      # bits 11:8  → imm[4:1]
            imm_10_5 = (instr >> 25) & 0x3F     # bits 30:25 → imm[10:5]
            imm_12   = (instr >> 31) & 0x1      # bit 31     → imm[12]

            imm = (imm_12 << 12) | (imm_11 << 11) | (imm_10_5 << 5) | (imm_4_1 << 1)
            imm = sign_extend(imm, 13)

            val1 = self.state.read_reg(rs1)
            val2 = self.state.read_reg(rs2)

            if funct3 == 0x0:
                taken = val1 == val2                              # beq
            elif funct3 == 0x1:
                taken = val1 != val2                              # bne
            elif funct3 == 0x4:
                taken = to_signed(val1) < to_signed(val2)         # blt
            else:
                raise ValueError(f"unsupported branch funct3: {funct3:#x} at pc={self.state.pc:#x}")

            if taken:
                next_pc = self.state.pc + imm

        elif opcode == 0x6F:
            rd = (instr >> 7) & 0x1F
            imm_20    = (instr >> 31) & 0x1
            imm_10_1  = (instr >> 21) & 0x3FF
            imm_11    = (instr >> 20) & 0x1
            imm_19_12 = (instr >> 12) & 0xFF

            imm = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1)
            imm = sign_extend(imm, 21)

            self.state.write_reg(rd, self.state.pc + 4)
            next_pc = self.state.pc + imm

        elif opcode == 0x67:
            funct3 = (instr >> 12) & 0x7

            if funct3 != 0x0:
                raise ValueError(f"unsupported JALR funct3: {funct3:#x} at pc={self.state.pc:#x}")
            
            rd = (instr >> 7) & 0x1F
            rs1 = (instr >> 15) & 0x1F
            imm = sign_extend((instr >> 20) & 0xFFF, 12)

            target = (self.state.read_reg(rs1) + imm) & 0xFFFFFFFE

            self.state.write_reg(rd, self.state.pc + 4)
            next_pc = target

        elif opcode == 0x37:
            rd = (instr >> 7) & 0x1F
            imm = instr & 0xFFFFF000

            self.state.write_reg(rd, imm)

        else:
            raise ValueError(f"unsupported opcode: {opcode:#x} at pc={self.state.pc:#x}")
        
        
        
        self.state.pc = next_pc
        
        
    def load_program(self, words, start=0):
        for i, word in enumerate(words):
            self.state.store_word(start + i * 4, word)
        self.state.pc = start

    def run(self, max_steps=1000):
        for _ in range(max_steps):
            if self.state.halted:
                break
            self.step()

    

if __name__ == "__main__":
    e = Emulator()

e.load_program([
        0x00000093,    # addi x1, x0, 0
        0x00100113,    # addi x2, x0, 1
        0x00B00193,    # addi x3, x0, 11
        0x00310863,    # beq  x2, x3, +16   (to ecall)
        0x002080B3,    # add  x1, x1, x2
        0x00110113,    # addi x2, x2, 1
        0xFF1FF06F,    # jal  x0, -16       (back to beq)
        0x00000073,    # ecall
    ])
e.run()
print(e.state.read_reg(1))    # expect 55

               