leti r1, 48 ; 
leti r2, 12 ;

gcd:
    bge r1,r2, end
    sub r1,r1,r2
    sub r2, r1, r1

end:
    bne r1, r2, gcd