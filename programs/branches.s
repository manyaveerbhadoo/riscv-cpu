        addi x1, x0, 7
        addi x0, x1, 1
        beq  x0, x1, done
        addi x2, x0, 1
        bne  x0, x1, done
        addi x3, x0, 99
done:   ecall
