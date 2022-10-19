A: .word 78
B: .word 85 
C: .word 0 

loop:
     load R2, [A]
     load R3, [B]
     bgeu R3, R2, loop
     store [C], R3

     bra +0
