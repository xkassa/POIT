import RPi.GPIO as GPIO
import time
import pygame
import os

time.sleep(8)
startf=open("static/files/run.txt","w")
startf.write("aaaa")
startf.close()
print('StartDrive.py')

def stop():
    stopf= open("static/files/run.txt", "w")
    stopf.write("stop")
    stopf.close()

def stoptest():
    stopf= open("static/files/run.txt", "r")
    stopt=(stopf.read(4))
    stopf.close()
    if stopt=="stop":
        istop=1;
    else:
        istop=0
        
    return istop

pygame.init()
testPS3=pygame.joystick.get_count()
print(testPS3)
if testPS3==1:
    j = pygame.joystick.Joystick(0)
    j.init()
    print('Initialized Joystick : %s' % j.get_name())
else:
    print('PS3 controller nieje pripojeny, koncim script')
    stop()
    os._exit(0)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(17,GPIO.OUT)
s=GPIO.PWM(17,50)
s.start(7)

GPIO.setup(18,GPIO.OUT)
mf=GPIO.PWM(18,100)
mf.start(0)

GPIO.setup(23,GPIO.OUT)
mr=GPIO.PWM(23,100)
mr.start(0)

GPIO.setup(22,GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(27,GPIO.OUT, initial=GPIO.LOW)

GPIO.output(22, GPIO.HIGH)
GPIO.output(27, GPIO.HIGH)

anglediff=0
enginerunstart=False
S1=7+anglediff
MF=0
MR=0
Uhol=0
Rychlost=0
Treshold=0.2
TresholdS=0.05
dist=50
counter=0

def setcar():
    s.ChangeDutyCycle(S1)
    mf.ChangeDutyCycle(MF)
    mr.ChangeDutyCycle(MR)
    
try:   
    while True:      
        events = pygame.event.get()
        for event in events:
          UpdateMotors = 0
          if event.type==pygame.JOYBUTTONDOWN:
                if event.button==10:
                    print('Client has Disconnected, ending script')
                    stop()
                    GPIO.cleanup()
                    quit()
                elif event.button==9:
                    enginerunstart=not enginerunstart
                    if enginerunstart:
                        print("Motor zapnuty")
                    time.sleep(0.3)
                elif event.button==5:
                    if anglediff<0.5:
                        anglediff=anglediff+0.1
                        print(anglediff)
                    time.sleep(0.2)
                elif event.button==4:
                    if anglediff>-0.5:
                        anglediff=anglediff-0.1
                        print(anglediff)
                    time.sleep(0.2)
                
          if event.type == pygame.JOYAXISMOTION:
            if event.axis == 1:
              Rychlost = event.value
              UpdateMotors = 1
            elif event.axis == 3:
              Uhol = event.value
              UpdateMotors = 1
              
            if UpdateMotors:
                aUhol=abs(Uhol)
                if (aUhol > TresholdS):
                  S1=round(Uhol*1.5+7+anglediff,2)
                  if S1>8.5:
                      S1=8.5
                  if S1<5.5:
                      S1=5.5                
                else: S1=7+anglediff
                
                if (Rychlost < -Treshold):
                  MF=-Rychlost*90
                else: MF=0
                
                if (Rychlost > Treshold):
                  MR=Rychlost*50
                else:
                  MR=0             
                if (MR>0 and MF>0):
                    MR=0
                    MF=0              
                if (enginerunstart):
                    setcar()               
                else:
                    if counter==19:
                        print('Motor vypnuty')
                    MR=0
                    MF=0
                    S1=7+anglediff
                    setcar()      
        time.sleep(0.05)
        counter=counter+1
        if counter==20:
            counter=0
            if stoptest():
                print('App.py called to stop')
                GPIO.cleanup()
                quit()
        
except KeyboardInterrupt:
    GPIO.cleanup()