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

startf=open("run.txt","w")
startf.write("aaaa")
startf.close()
time.sleep(0.5)
print('StartApp.py')

def stop():
    stopf= open("run.txt", "w")
    stopf.write("stop")
    stopf.close()

def stoptest():
    stopf= open("run.txt", "r")
    stopt=(stopf.read(4))
    stopf.close()
    if stopt=="stop":
        istop=1;
    else:
        istop=0
    return istop

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

async_mode = None
app = Flask(__name__)

config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print myhost

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 
runvariable='nieco'
dbV='nieco'

def background_thread(args):
    dataList = []
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)  
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
        if stoptest():
            print('Drive.py called to stop')
            os._exit(0)
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
                if dbV == 'start':
                  print('zapisujem do suboru')
                  dataDict = {
                    "N": count/20,
                    "Ax": round(uholx),
                    "Ay": round(uholy),
                    "Dist": (round(40-(dist+dist1+dist2)/3))}
                  dataList.append(dataDict)
                  
                else:
                  if len(dataList)>0:
                    print (str(dataList))
                    fuj = str(dataList).replace("'", "\"")
                    print fuj
                    fo = open("static/files/test.txt","a+")    
                    fo.write(str(fuj)+"\r\n")
                    fo.close()
                    
                    cursor = db.cursor()
                    cursor.execute("SELECT MAX(id) FROM graph")
                    maxid = cursor.fetchone()
                    cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, fuj))
                    db.commit()
                    print('zapisane do suboru a do databazy')
                  dataList = []
                  dataCounter = 0 

@app.route('/', methods=['GET', 'POST'])
def graphlive():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    print('Client has Disconnected, ending script')
    stop()
    os._exit(0)
    
@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)

@app.route('/dbdata/<string:num>', methods=['GET', 'POST'])
def dbdata(num):
  num = int(num)
  numstr1 = str(int((num + 1)/10))
  numstr2 = str((num + 1) - int((num + 1)/10)*10)
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute("SELECT hodnoty FROM graph WHERE id=%s%s" % (numstr1, numstr2))
  rv = cursor.fetchone()
  return str(rv[0])

@app.route('/db')
def db():
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute('''SELECT  hodnoty FROM  graph WHERE id=1''')
  rv = cursor.fetchall()
  return str(rv)    

@app.route('/graphtxt', methods=['GET', 'POST'])
def graphtxt():
    return render_template('graphtxt.html', async_mode=socketio.async_mode)

@app.route('/read/<string:num>')
def readmyfile(num):
    fo = open("static/files/test.txt","r")
    rows = fo.readlines()
    fo.close()
    return rows[int(num)-1]

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
    
@socketio.on('start_event', namespace='/test')
def run_message(message):
    global runvariable
    runvariable = message['value']
    if runvariable=="start":
        print(runvariable)
    else:
        print('nemeriam veliciny')


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
    
