from pytoy.infra.timertask import TimerTask 


global MY_NUMBER 
#MY_NUMBER = 100

def func():
    global MY_NUMBER 
    MY_NUMBER += 1

TimerTask.register(func, interval=10)
import time
time.sleep(0.5)

print(MY_NUMBER) 
