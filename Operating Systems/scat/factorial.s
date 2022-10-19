leti r1, 1
leti r2, 0
leti r3, 0

loop:
    mul r3, r3, r2
    ;add r2, r2, 1
    bne r2, r1, loop
    bra +0

