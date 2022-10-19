#!/usr/bin/env python3

import tkinter as tk
import re
import sys
import multiprocessing as mp
import signal
import time

import collections



class GUI(tk.Tk):
    def __init__(self,xres=80,yres=60,data=None):
        self.xres=xres
        self.yres=yres

        self.data=data
        
        super().__init__()
        self.title("Scat")
        self.canvas = tk.Canvas(self,
                                background="grey50", # background color, only shows during resize
                                borderwidth=0,highlightthickness=0)
        self.img=tk.PhotoImage() # placeholder object (actual rendering happens in `update()`) 
        self.canvas.img_id=self.canvas.create_image(0,0,image=self.img,anchor=tk.NW)
        self.canvas.pack(fill=tk.BOTH,expand=1)
        
        ####################
        # zoom factor guessing: window starts centered, roughly 1/3rd of screen space
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        zf=int(min(sw/xres/3, sh/yres/3))
        self.geometry(f'{xres*zf}x{yres*zf}+{(sw-xres*zf)//2}+{(sh-yres*zf)//2}')
        self.aspect(xres,yres,xres,yres)
        self.minsize(xres, yres)

        self.zoom_factor = zf   # current zoom factor
        self.zoom_wanted = None # new zoom factor
        self.zoom_max    = min( int((sh-50) / yres), int((sw-50) / xres))

        self.bind("<Configure>", self.on_resize)
        self.update() # call once to start the "after()" loop
        
    def on_resize(self,event):
        # Handle window resizing. Note that all actual work happens in
        # `update()` to avoid various issues (inconsistencies, seg fault)
        xratio = round(event.width/self.xres)
        yratio = round(event.height/self.yres)
        if xratio == self.zoom_factor:
            self.zoom_wanted=yratio
        elif yratio == self.zoom_factor:
            self.zoom_wanted=xratio
        else:
            self.zoom_wanted=max(xratio,yratio)
            # safety check, useful e.g. at startup when configure() is called with a 1x1 window size (!) 
        if self.zoom_wanted <1:
            self.zoom_wanted=1
        if self.zoom_wanted >self.zoom_max:
            self.zoom_wanted=self.zoom_max
        # print(f"on_resize(): {event.width}x{event.height} ~ {xratio}x{yratio} : {self.zoom_factor} -> {self.zoom_wanted}")

    # as per https://stackoverflow.com/a/63630091/117814
    # def __del__(self):
    #     print("GUI closed")
    #     for after_id in self.tk.eval('after info').split():
    #         print("canceling ",after_id)
    #         self.after_cancel(after_id)

    def update(self):
        self.after(30,self.update) # 30 ms ~ 100FPS
        try:
            super().update()
        except tk.TclError: # happens e.g. when the window is closed
            # print('TclError')
            return

        if self.zoom_wanted:
            zf=self.zoom_factor = self.zoom_wanted
            self.geometry(f'{zf*self.xres}x{zf*self.yres}')
            self.zoom_wanted = None
        try:
            ppmdata=f"P6 {self.xres} {self.yres} 255 ".encode('ascii')+self.data.raw
            self.img=tk.PhotoImage(data=ppmdata).zoom(self.zoom_factor)
            self.canvas.itemconfig(self.canvas.img_id,image=self.img)
        except tk.TclError:
            # print('TclError')
            return
        except RuntimeError:
            # when the window is closed, we get an error "Too early to create image"
            # print('RuntimeError')
            return

def on_delete_window(gui):
    # print("WM_DELETE_WINDOW")
    for after_id in gui.eval('after info').split():
        # print("after_cancel ",after_id)
        gui.after_cancel(after_id)
    gui.destroy()

def gui_loop(xres,yres,data):
    gui=GUI(xres,yres,data)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # as per https://stackoverflow.com/a/63630091/117814
    gui.protocol('WM_DELETE_WINDOW', lambda: on_delete_window(gui))
    try:
        gui.mainloop()
    except Exception as e:
        # print("gui error:",e)
        raise
        
class Screen():
    def __init__(self,xres=80,yres=60):
        ########################################
        # Scat stuff

        # pixel resolution of our video memory
        self.xres=xres
        self.yres=yres

        # three bytes per pixel mimics the tk-friendly P6 PPM format 
        self.data=mp.Array('c',xres*yres*3)

        # dummy process just for is_alive()
        self.process=mp.Process() 

    def show(self):
        if self.process.is_alive():
            return

        self.process=mp.Process(target=gui_loop, args=(self.xres,self.yres,self.data))
        self.process.daemon=True # maybe fixes the "tried to destroy photoimage" error
        self.process.start()

    def close(self):
        if self.process.is_alive():
            self.process.terminate()
            #print('closed')
        
    def read(self,reladdr,size):
        if reladdr >= self.xres*self.yres*4:
            print("error: relative address is outside screen range: 0x%x\n" % reladdr)
            sys.exit(1)
        # for now we only support single pixels
        assert reladdr % 4 == 0
        voffset = (reladdr//4)*3 # offset in video array (3 bytes per pixel)

        return (  (int.from_bytes(self.data[voffset  ],byteorder="little")<<24)
                + (int.from_bytes(self.data[voffset+1],byteorder="little")<<16)
                + (int.from_bytes(self.data[voffset+2],byteorder="little")<<8))
        
    def write(self,reladdr,data):
        # Note: reladdr is zero-based within the framebuffer
        if reladdr >= self.xres*self.yres*4:
            print("error: relative address is outside screen range: 0x%x\n" % reladdr)
            sys.exit(1)
        # for now we only support single pixel writes
        assert reladdr % 4 == 0

        voffset = (reladdr//4)*3 # offset in video array (3 bytes per pixel)

        # 24-bit value to 3 bytes in big-endian order
        self.data[voffset] =   (data >>24) & 0xFF
        self.data[voffset+1] = (data >>16) & 0xFF
        self.data[voffset+2] = (data >> 8) & 0xFF
        self.dirty = True

        
if __name__ == '__main__':

    win=Screen(80,60)

    win.show()
    
    # try:
    #     for i in range(59,0,-1):
    #         win.write(i*80*4+i*4,0xFFFFFFFF)
    #         print(i)
    #         time.sleep(.1)
    # except KeyboardInterrupt:
    #     pass

    x=15
    y=10
    dx=1
    dy=-1

    try:
        while True:
            win.write((x+y*80)*4,0x88888888)
            x+=dx
            y+=dy
            win.write((x+y*80)*4,0xFF000000)
            if x==0 or x==79: dx*=-1
            if y==0 or y==59: dy*=-1
            time.sleep(.05)

            if not win.process.is_alive():
                break
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("main process error:",e)
        
    
    win.close()
