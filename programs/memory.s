        addi x1, x0, 0x100
        lui  x2, 0xDEAD0
        addi x2, x2, 0xEF
        sw   x2, 0(x1)
        lw   x3, 0(x1)
        ecall
