
array: 
    .word 10, 9, 14, 13, 15

start:
    load r0, [array]
    load r1, [r0]
    mov r2, r1


loop:
    load r1, [r0]
    ;cmp r2, r2
    call loop1
    subi r5, r5, 1
    caLL halt 
    

loop1:
    mov r2, r1
    subi r5,r5,1
    call halt 
    

halt:
    bra +0