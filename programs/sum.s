# sum 1..10, result in x1

        addi x1, x0, 0
        addi x2, x0, 1
loop:   addi x3, x0, 11
        beq  x2, x3, done
        add  x1, x1, x2
        addi x2, x2, 1
        jal  x0, loop
done:   ecall
