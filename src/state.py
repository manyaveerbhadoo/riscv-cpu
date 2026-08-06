

class MachineState:
    def __init__(self, pc=0):
        self.pc = pc
        self.regs = [0] * 32
        self.mem = {}
        self.halted = False

    def read_reg(self, i):
        return self.regs[i]

    def write_reg(self, i, value):
        if i == 0:
            return
        self.regs[i] = value & 0xFFFFFFFF

    def store_word(self, addr, value):              #writes a 32-bit word to an address
        value = value & 0xFFFFFFFF
        for k in range(4):
            self.mem[addr + k] = (value >> (8 * k)) & 0xFF

    def load_word(self, addr):
        value = 0
        for k in range(4):
            byte = self.mem.get(addr + k, 0)
            value |= byte << (8 * k)
        return value

    def dump(self):
        return {
            "pc": self.pc,
            "regs": list(self.regs),
            "mem": {
                addr: self.mem[addr]
                for addr in sorted(self.mem)
                if self.mem[addr] != 0
            },
        }
    




