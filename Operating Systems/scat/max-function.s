A: .word 12
B: .word 24

load r1, [A]
load r1, [r1]
load r2, [B]
load r2, [r2]

blt r1, r2, end
mov r1, r2
store [B], r3
end:
    bra +0