leti r3, 5
leti r1, 5


factorial:
beq r0, r1,end 
    subi r1, r1, 1 
    mul r3, r3, r1
    
    call factorial 

    end:

        bra  +0