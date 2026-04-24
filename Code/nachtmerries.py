# coole shit voor gedeelde variabel

import threading
import time
import random

# global variable
sigma_pid = 0

# thread lock
lock = threading.Lock()

class coolethread(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        print(f"{self.name} is running.")
        
        while True:
            global sigma_pid
            random_value = random.randint(0, 100)
            with lock:
                sigma_pid = random_value
        
class coolethread2(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        print(f"{self.name} is running.")
        
        while True:
            global sigma_pid
            random_value = random.randint(-100, 0)
            with lock:
                sigma_pid = random_value

if __name__ == "__main__":
    thread1 = coolethread("Thread-1")
    thread2 = coolethread2("Thread-2")
    
    thread1.start()
    thread2.start()
    
    while True:
        print(f"Current sigma_pid: {sigma_pid}")
        time.sleep(1/30)