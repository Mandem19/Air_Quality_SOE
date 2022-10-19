main: 
     leti r1, 0
     leti r2, 0
     leti r3, 0xFF00FF00
     call drawpixel

     leti r1, 0
     leti r2, 59
     leti r3, 0xFFA50000
     call drawpixel
     
     leti r1, 79
     leti r2, 0
     leti r3, 0x00FF0000
     call drawpixel

     leti r1, 79
     leti r2, 59
     leti r3, 0xFF000000
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
