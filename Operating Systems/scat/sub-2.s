main: 
     leti r1, 0
     leti r2, 0
     leti r3, 0xFFF00
     call drawpixel

     leti r1, 0
     leti r2, 59
     leti r3, 0x0000FF
     call drawpixel
     
     leti r1, 79
     leti r2, 0
     leti r3, 0xFF0000
     call drawpixel

     leti r1, 79
     leti r2, 59
     leti r3, 0x0FF00
     call drawpixel
     bra +0

drawpixel:
        muli R1, R1, 4
        muli R2, R2, 320
        add R7, R2, R1
        leti R4, 0xB0000000 ; VRAM base address
        add R5, R4, R7

        store [r5], r3
        ret
