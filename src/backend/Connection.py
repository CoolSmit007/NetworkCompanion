from Socket import socketClass
from ServerSocket import serverSocketClass
from models.DataTypeEnum import DataType

import queue
import threading as th
import logging
import json
import sys

class connection:
    __logger = logging.getLogger()
    __receiveLock = th.Event()
    
    def __init__(self):
        self.socket = socketClass()
        self.server = serverSocketClass()
        self.fileQueue = queue.Queue()
        self.folderQueue = queue.Queue()
        self.screenQueue = queue.Queue()
        self.audioQueue = queue.Queue()
        self.keyboardQueue = queue.Queue()
        self.mouseQueue = queue.Queue()
        
    def receive(self):
        while self.__receiveLock.is_set():
            data = self.socket.receiveQueue.get()
            
            if(not isinstance(data, bytes)):
                self.__logger.error("Data is not a bytearray")  
                continue
            
            try:
                decodedData = data.rstrip('\x00').decode()
            except UnicodeDecodeError as error:
                self.__logger.error("Unicode Decode error %s",error)  
                continue
            
            if(not decodedData[-1]=='\n'):
                self.__logger.error("Data doesn't contain \\n as the last character")  
                continue
            
            try:
                jsonData = json.loads(decodedData[:-1])
            except json.JSONDecodeError as error:
                self.__logger.error("JSON Decode error %s",error)  
                continue
            
            bytesDataLength = jsonData.get("data_length")
            paddedLength = jsonData.get("padding_length")
            typeOfData = jsonData.get("type")
            
            if not bytesDataLength:
                self.__logger.error("No attribute 'data_length' found in JSON")  
                continue
            
            if not paddedLength:
                self.__logger.error("No attribute 'padded_length' found in JSON")  
                continue
            
            if not typeOfData:
                self.__logger.error("No attribute 'type' found in JSON")  
                continue
                
            finalData=bytes()
            while bytesDataLength>len(finalData):
                finalData += self.socket.receiveQueue.get()
                
            if(bytesDataLength!=len(finalData)):
                self.__logger.error("JSON final bytes length doesn't match data_length, data_length=%d, len of final bytes=%d",bytesDataLength,len(finalData))  
                continue
            
            if not all(bytesValue==b'\x00' for bytesValue in finalData[-paddedLength:]):
                self.__logger.error("Not all padded bytes are null bytes for padding_length=%d",paddedLength)  
                continue
            
            finalData = finalData[:-paddedLength] if paddedLength > 0 else finalData
                
            match typeOfData:
                case DataType.COMMAND.value:
                    pass
                case DataType.AUDIO.value:
                    self.audioQueue.put(finalData)
                case DataType.SCREEN.value:
                    self.screenQueue.put(finalData)
                case DataType.FILE.value:
                    self.fileQueue.put(finalData)
                case DataType.FOLDER.value:
                    self.folderQueue.put(finalData)
                case DataType.KEYBOARD.value:
                    self.keyboardQueue.put(finalData)
                case DataType.MOUSE.value:
                    self.mouseQueue.put(finalData)
            
    def send(self,type,data):
        if not isinstance(data,bytes):
            self.__logger.error("Data is not of type bytes")  
            raise Exception("Data is not of type bytes")
        
        if not isinstance(type,DataType):
            self.__logger.error("Type is not an enum of type DataType")  
            raise Exception("Type is not an enum of type DataType")
        
        padLength = (1024-(len(data)%1024))%1024
        jsonData = {"type":type.value, "data_length":len(data)+padLength,"padding_length":padLength}
        encodedJSONData = (json.dumps(jsonData)+'\n').encode().ljust(1024, b'\x00')
        paddedData = data.ljust(len(data) + padLength, b'\x00')
        self.socket.sendData(encodedJSONData)
        self.socket.sendData(paddedData)
            
                