        addi a0, zero, 5
        jal  ra, double
        addi a1, a0, 1
        ecall
double: add  a0, a0, a0
        jalr zero, ra, 0
