from MESA import *

if __name__ == '__main__':

    while True:
        mesa.wait_cycle(TIC)
        blinken(0x01, B2)

        if read(0x01) == POS_FLANKE:
            mesa.P1 ^= 0x01
