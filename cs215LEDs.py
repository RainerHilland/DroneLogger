#! /usr/bin/env python

# for importing to the logger script to keep it clean

import RPi.GPIO as GPIO
import time

GPIO.setwarnings(False) # because otherwise the program yells at you

# pin definitions
p_red = 40
p_green = 38
p_blue = 36

def p_on(pin):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)


def p_off(pin):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


def led_red():
    p_on(p_red)
    p_off(p_green)
    p_off(p_blue)


def led_blue():
    p_off(p_red)
    p_off(p_green)
    p_on(p_blue)


def led_mag():
    p_on(p_red)
    p_off(p_green)
    p_on(p_blue)


def led_green():
    p_off(p_red)
    p_on(p_green)
    p_off(p_blue)


def led_off():
    p_off(p_red)
    p_off(p_green)
    p_off(p_blue)


def led_blink(n, t, col):
    for i in range(0,n):
        if col == 'red': # lol great work here
            led_red()
        elif col == 'mag':
            led_mag()
        else:
            break
        time.sleep(t)
        led_off()
        time.sleep(t)
