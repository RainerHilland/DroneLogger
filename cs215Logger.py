#! /usr/bin/env python

"""

Logging program for R-Pi for use on drone-based platform for the
NamTEX 2020 campaign.

Rainer Hilland

Borrows from Dr. Liu's code for the SDI-12 communication, see
 https://liudr.wordpress.com/gadget/sdi-12-usb-adapter/
The GpsPoller class is from Dan Mandle, see
 http://dan.mandle.me
But really the GPS code is taken from Heinz & Andreas Christen and the MeteoBike project

Assumes the SDI-12 bus has a constant port defined and that only 1 sensor is on
 the bus with SDI address 0

This script is all set up to run on boot - only need to include the
 execution line in  /etc/rc.local on the pi

~*~* General Description *~*~

 - This script is set to log one CS-215 probe and one Adafruit GPS dongle through a R-Pi Zero W
 - When rc.local is correctly configured it will run headless on boot
 - Each new boot creates a new log file and puts it on the desktop. It logs:
    - Record number (resets on reboot)
    - GPS and RPi time
    - T
    - RH
 - There is no set logging/sampling interval, nor an imposed delay. The script simply runs as
    quickly as possible. This mostly results in a ~1 second sample rate, though sometimes measurements
    occur twice in one second or once in two seconds
 - It contains an LED for status
 	- Constant red: script initialising
 	- 5 Red blinks: successfully opened com port to SDI-12 hat
 	- 5 purple blinks: succesfully found CS215 probe
 	- Blinking blue: logging, but no GPS
 	- Blinking green: logging with GPS
 	- LED off: script not running
 	- A solid red after blinking to open the com port means no SDI device was found w/ address 0
 - Time
    - The time is written as GPS time and RPi time
    - GPS time is recorded in UTC but of course only when GPS has a fix
    - RPi time is whatever time the onboard clock of the GPS thinks it is. This is likely to NEVER
       be accurate; there is no battery powering a clock on the RPi.
    - The file names are created based on the Pi time to ensure that an actual new file is created
       on each re-start

~*~* noitpircseD lareneG *~*~
 
Notes:
 - A better way to verify the location of the SDI bus would be to check its v.idn from the list of ports,
    however in practice it has always found its way to ID = 0 and it will be the only thing plugged in 
    for this application.
     - NB: the SDI hat has vidn 0403, which is parsed as 1027, should you want to implement the above

"""

# necessary packages
import serial.tools.list_ports
import serial
import time, board, busio, os
import adafruit_bmp280
from gps import *
import threading
from cs215LEDs import *
#import re

led_red() # start by setting LED to red

#######
# Classes and functions
#######

# GPS class
class GpsPoller(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        global gpsd # bring in scope
        gpsd = gps(mode=WATCH_ENABLE) # starting gps stream
        self.current_value = None
        self.running = True # thread is running
    def run(self):
        global gpsd
        while gpsp.running:
            gpsd.next() # this will continue to loop and grab each set of gpsd info to clear the buffer


def check_sdi():

	''' This function just ensures that there 
	is an SDI device connected with address 0 '''

    ser.write(b'?!') # command to identify all SDI-12 devices on bus
    sdi_12_line = ser.readline() # get response
    sdi_12_line = sdi_12_line[:-2] # remove /r /n

    m = re.search(b'[0-9a-zA-Z]$', sdi_12_line) # pick out the useful characters
    sdi_12_address = m.group(0)

    if int(sdi_12_address) == 0: # If only one address comes back and it's 0, flash LED in approval
        led_blink(5,0.25,'mag')
    else:
        led_red() # error LED if no SDI device found


def createLog(logfile):

    ''' Creates the logged file and writes a header - to run once per boot
    arg: logfile is a string pointing to the file to be created '''
    
    f0=open(logfile,'w') # header: variables and units
    f0.write('record,gps_time,rpi_time,altitude,latitude,longitude,probe_temp,relHumidity,bmp_temp,bmp_press\n')
    f0.write('NA,UTC(GPS),NA,m,DDMM.MMMM,DDDMM.MMMM,degC,percent,degC,Pa\n')
    f0.close()
    

def split(string):
    return [char for char in string]


def sample(logfile):
    
    ''' Samples the GPS, CS215, and BMP280 and writes an entry in the log '''

    global record # bring variables in to scope
    global sdi_12_address

    record += 1 # just a record number
    piTime = time.strftime('%Y-%m-%d %H:%M:%S') # get time from onboard clock

    # sample the GPS
    gps_time = gpsd.utc
    gps_altitude = gpsd.fix.altitude
    gps_latitude = gpsd.fix.latitude
    gps_longitude = gpsd.fix.longitude
    f_mode = int(gpsd.fix.mode) # stores number of satellites
    has_fix = False # assumes no fix
    if f_mode > 2:
        has_fix = True # if more than 2 satellites, gps has fix
    
    # sample the cs215 probe
    ser.write(sdi_12_address+b'M!') # measurement command
    sdi_12_line=ser.readline()
    sdi_12_line=ser.readline()
    ser.write(sdi_12_address+b'D0!') # transmit measurement command
    sdi_12_line = ser.readline()
    sdi_12_line = sdi_12_line[:-2] # gets rid of tailing \r and \n

    meas = sdi_12_line.decode('utf-8')
    #meas = re.split('\+',meas) # V3: REMOVED - doesn't work for negative values, not safe
    meas = split(meas)
    temp = meas[1]+meas[2]+meas[3]+meas[4]+meas[5]+meas[6]+meas[7] # brute force!
    rh = meas[8]+meas[9]+meas[10]+meas[11]+meas[12]+meas[13]+meas[14]

    # write a line to the logging file
    f0 = open(logfile, 'a') # open the logging file in amend mode
    f0.write(str(record)+',')
    if has_fix:
        f0.write(gps_time+',')
        led_green()
    else:
        f0.write('no_fix,')
        led_blue()
    f0.write(piTime+',')
    f0.write(str(gps_altitude)+',')
    f0.write(str(gps_latitude)+',')
    f0.write(str(gps_longitude)+',')
    f0.write(str(temp)+',')
    f0.write(str(rh)+',')
    f0.write(str(bmptemp+','))
    f0.write(str(bmppress+'\n'))
    f0.close()

    led_off()

    # If not running headless these can help monitor the sensor streams
	#print(gps_time+' '+str(gps_latitude)+' '+str(gps_longitude)+' '+str(gps_altitude))
	#print(str(temp)+' '+str(rh))
    

#####
# Start of main body
#####

# set the log file
logfile_path = '/home/pi/Desktop/'
logfile = logfile_path+'DroneLog-'+time.strftime("%Y-%m-%d %H:%M:%S.csv") # these times are inaccurate of course
																		  # but it ensures no file is overwritten
record = 0

# initialise the gps thread
gpsd = None
gpsp = GpsPoller()
gpsp.start()

# initialise the SDI bus
sdi_12_address = b'0' # address for the instrument
ports = serial.tools.list_ports.comports() # pulls up all the comports
port_device = ports[0].device # define the SDI bus by assuming it's number 0
ser = serial.Serial(port=port_device,baudrate=9600,timeout=10) # open communications
time.sleep(2.5) # allow bus to boot

led_off()
led_blink(5,0.25,'red') # status indicator

check_sdi() # check that we can talk to an instrument on the bus

# initialise the I2C bus for BMP280
i2c = busio.I2C(board.SCL, board.SDA)
bmp = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)

# run the logger
createLog(logfile)
while True:
    sample(logfile) # WOOHOO LOG THAT DATA

# Note: a good script would clean up the LED stuff with GPIO.cleanup() but if we're running infinitely
# I don't know how to do that.


