from state import MachineState


def to_signed(value):
    if (value >> 31) & 1:
        return value - 0x100000000
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
            
            elif funct3 == 0x7:
                result = val1 & val2
            elif funct3 == 0x6:
                result = val1 | val2
            elif funct3 == 0x4:
                result = val1 ^ val2
            elif funct3 == 0x2:
                result = 1 if to_signed(val1) < to_signed(val2) else 0
            
            else:
          
                raise ValueError(f"unsupported funct3: {funct3:#x} at pc={self.state.pc:#x}")

            self.state.write_reg(rd, result)
        elif opcode == 0x73:
            self.state.halted = True

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
    e.state.write_reg(1, 10)
    e.state.write_reg(2, 3)
    e.load_program([0x00208533, 0x00000073])
    e.run()
    print(e.state.read_reg(10))   # expect 13
    print(e.state.pc)             # expect 8 
               