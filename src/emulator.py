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
        0x00A00093,    # addi x1, x0, 10
        0x06400113,    # addi x2, x0, 100
        0x00112023,    # sw   x1, 0(x2)     → memory[100] = 10
        0x00012183,    # lw   x3, 0(x2)     → x3 = memory[100]
        0x00000073,    # ecall
    ])
e.run()
print(e.state.read_reg(3))    # expect 10

               