
A: .word 20
B: .word 40
C: .word 0

load R0, [A]
load R0, [R0]
load R1, [A]
load R1, [R1]

;cmp R0, R1 ?? - What is CMP
mov R1, R0
store [C], R0