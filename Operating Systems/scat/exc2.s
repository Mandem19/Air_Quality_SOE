
leti r3, 10
leti r4, 15

loop:
    bge r3,r4, loop
    store [r5], r4 
    bra +0