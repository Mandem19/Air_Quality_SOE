
Array: .word 13, 18, 5, 3, 10
Lenght: .word 5

load R0, [Array]
load R1, [Lenght]
load R1, [R1]

subi R1, R1, 0
bra +0
load R2, [R0]
mov R3, R2
addi R0, R0, 4
subi R1, R1, 1


loop1:
     subi R1, R1, 0
     bra +0
     load R2, [R0]
     mov R3, R2
     addi R0, R0, 4
     subi R1, R1, 1
     
end:
    mov R1, R3
    bra +0
     
