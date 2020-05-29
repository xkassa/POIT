from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect  
import time
import random
import math
import smbus
import os
import RPi.GPIO as GPIO
import MySQLdb 
import ConfigParser

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO_TRIGGER = 24
GPIO_ECHO = 21

GPIO.setup(24, GPIO.OUT)
GPIO.setup(21, GPIO.IN)


def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
    
    return distance


# Register
power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c

def read_byte(reg):
    return bus.read_byte_data(address, reg)
 
def read_word(reg):
    h = bus.read_byte_data(address, reg)
    l = bus.read_byte_data(address, reg+1)
    value = (h << 8) + l
    return value
 
def read_word_2c(reg):
    val = read_word(reg)
    if (val >= 0x8000):
        return -((65535 - val) + 1)
    else:
        return val
 
bus = smbus.SMBus(1) 
address = 0x68     
bus.write_byte_data(address, power_mgmt_1, 0)

def MPU_9265_getdata():  
    gxout = read_word_2c(0x43)
    gyout = read_word_2c(0x45)
    gzout = read_word_2c(0x47)
    xout = read_word_2c(0x3b)
    yout = read_word_2c(0x3d)
    zout = read_word_2c(0x3f)
    xout=xout/ 16384.0
    yout = yout / 16384.0
    zout = zout / 16384.0
    return gxout,gyout,gzout,xout,yout,zout

def write2file(Ax,Ay,dist,n):
    fo = open("static/files/test.txt","a+")    
    val = '[{"y": 0.6551787400492523, "x": 1, "t": 1522016547.531831}, {"y": 0.47491473008127605, "x": 2, "t": 1522016549.534749}, {"y": 0.7495528524284468, "x": 3, "t": 1522016551.537547}, {"y": 0.19625207463282368, "x": 4, "t": 1522016553.540447}, {"y": 0.3741884249440639, "x": 5, "t": 1522016555.543216}, {"y": 0.06684808042190538, "x": 6, "t": 1522016557.546104}, {"y": 0.17399442194131343, "x": 7, "t": 1522016559.54899}, {"y": 0.025055174467733865, "x": 8, "t": 1522016561.551384}]'
    fo.write("%s\r\n" %val)
    return "done"



async_mode = None
app = Flask(__name__)



app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 
runvariable='nieco'
dbV='nieco'

def background_thread(args):
    dataList = []
    
    uholx=0
    uholy=0
    count=0
    countemit=0
    dtime=0.01
    dist=50
    dist1=50
    dist2=50
    
    ## put ka in range 0 to 1 better near 0
    ka=0.2
    while True:
        socketio.sleep(dtime)
        if runvariable=="start":
            gx,gy,gz,ax,ay,az=MPU_9265_getdata()
            uholx=ka*(uholx+gy*dtime)+(1-ka)*(math.atan(ay/(math.sqrt(ax*ax+az*az)))*180/math.pi)-5.4
            uholy=-ka*(uholy+gx*dtime)-(1-ka)*(math.atan(ax/(math.sqrt(ay*ay+az*az)))*180/math.pi)-21.5
            count += 1
            countemit +=1
            if (countemit == 20):
                dist=distance();
                if dist>40:
                    dist=40;
                socketio.emit('my_response',
                          {'anglex': round(uholx),'angley': round(uholy),'dist': (round(40-(dist+dist1+dist2)/3)),'gx': gx,'gy': gy,'gz': gz, 'count': count},
                          namespace='/test')  
                countemit=0;
                dist2=dist1;
                dist1=dist;
                

@app.route('/', methods=['GET', 'POST'])
def graphlive():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    print('Client has Disconnected, ending script')
    os._exit(0)
    




@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
            print('zaciatok spojenia')
    
@socketio.on('db_event', namespace='/test')
def db_message(message):
    global dbV
    dbV = message['value']
    print(dbV)
    



if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
    
