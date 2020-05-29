from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect  
import time
import random
import math
import smbus
import RPi.GPIO as GPIO


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






async_mode = None
app = Flask(__name__)



app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 


def background_thread(args):
    
    
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
        count += 1
        countemit +=1
        if (countemit == 20):
            dist=distance();
            if dist>40:
                dist=40;
            socketio.emit('my_response',
                      {'dist': (round(40-(dist+dist1+dist2)/3)),'count': count},
                      namespace='/test')  
            countemit=0;
            dist2=dist1;
            dist1=dist;
            dataCounter = 0 

@app.route('/', methods=['GET', 'POST'])
def graphlive():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    print('Client has Disconnected, ending script')
    quit()
    
@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
            print('zaciatok spojenia')


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
    
