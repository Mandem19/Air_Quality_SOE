main: 
     leti r1, 0
     leti r2, 0
     call drawpixel

        leti r1, 0
     leti r2, 0
     call drawpixel

     leti r1, 0
     leti r2, 59
     call drawpixel
     
     leti r1, 79
     leti r2, 0
     call drawpixel
     
     leti r1, 79
     leti r2, 59
     call drawpixel
     bra +0

drawpixel:
        muli R1, R1, 4
        muli R2, R2, 320
        add R3, R2, R1
        leti R4, 0xB0000000 ; VRAM base address
        add R5, R4, R3
        leti R6, 0xFFFF00 ; RGB hex triplet for magenta

        store [r5], r6
        ret
