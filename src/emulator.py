from state import MachineState

class Emulator:
    def __init__(self, state=None):
        self.state = state if state is not None else MachineState()

    #def load_program(self, words, start=0):
    def step(self):
        instr = self.state.load_word(self.state.pc)
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
                self.state.write_reg(rd, result)
            else:
                raise ValueError(f"unsupported funct3: {funct3:#x} at pc={self.state.pc:#x}")
            self.state.pc += 4

if __name__ == "__main__":
    e = Emulator()
    e.state.write_reg(1, 10)
    e.state.write_reg(2, 3)
    e.state.store_word(0, 0x40208533)     
    e.step()
    print(e.state.read_reg(10))          
    print(e.state.pc)                    