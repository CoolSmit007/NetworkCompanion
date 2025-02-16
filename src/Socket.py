import socket
import select
from collections import deque
import logging
import threading as th
class socketClass:
    logger = logging.getLogger()
    receiveLock = th.Event()
    receiveThread = None
    ip=None
    port=None
    def __init__(self, socketObject=None, ip=None, port=None):
        self.socket = socketObject if socketObject!=None else socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.ip=ip
        self.port=port
        self.receiveQueue = deque()
        self.receiveLock.set()
        
    @staticmethod
    def getPersonalIp():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ans=s.getsockname()
        s.close()
        return ans

    def sendData(self,data):
        select.select([],[self.socket.fileno()],[])
        self.socket.sendall(data)
        
    def receiveData(self):
        while self.receiveLock.is_set():
            try:
                select.select([self.socket.fileno()],[],[])
                recieve_data=self.socket.recv(1024)
                if not recieve_data:
                    self.closeSocket()
                    return
                self.receiveQueue.append(recieve_data)
            except ValueError as error:
                self.logger.error("Value error while receiving data: %s",str(error))
            except OSError as error:
                self.logger.error("OS error while receiving data: %s",str(error))
                
    def connect(self,ip,port):
        try:
            self.socket.connect((ip,port))
            return True
        except ConnectionRefusedError as error:
            self.logger.error("Connection refused error: %s",str(error))
            return False
        except TimeoutError as error:
            self.logger.error("Timeout error while trying to connect: %s",str(error))
            return False 
        except OSError as error:
            self.logger.error("OS error while trying to connect: %s",str(error))
            return False
           
    def startReceiveThread(self):
        self.receiveThread=th.Thread(target=self.receiveData)
        
    def closeSocket(self):
        self.receiveLock.clear()
        self.receiveThread.join(timeout=1000)
        if(self.receiveThread.is_alive()):
            return False
        self.socket.close()
        return True