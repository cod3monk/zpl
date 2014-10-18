#!/bin/env/python

import socket

class Printer:
    '''
    This abstract Printer class is used to interface with ZPL2 printers.
    '''
    def send_job(self, zpl2):
        print zpl2
    
    def get_info(self, command):
        raise Exception("not implemented in this printer class")
    
    def printer_info(self):
        if not self._info:
            ret = self.get_info('~HI').strip()
            m = re.match(r'(?P<model>[^,]+),(?P<version>[^,]+),(?P<dpmm>[^,]+),(?P<mem>[^,]+)', ret)
            self.info = m.groupdict()
        
        return self._info
    
    def get_label_dimensions(self):
        # TODO
        return (height, width)
    
    def get_dpi(self):
        '''returns dots per inch of printer.'''
        return self.get_dpmm()*25
    
    def get_dpmm(self):
        '''returns dots per millimeter of printer.'''
        return int(self.printer_info()['dpmm'])
        

class TCPPrinter(Printer):
    '''
    This class allows to interface with a ZPL2 printer via a TCP port.
    '''
    
    def __init__(self, host, port=9100):
        self.socket = socket.create_connection((host, port))
    
    def send_job(self, zpl2):
        self.socket.sendall(zpl2)
    
    def get_info(self, command):
        self.socket.sendall(command)
        return self.socket.recv(4096)
    
    def __del__(self):
        self.socket.close()

class FilePrinter(Printer):
    def __init__(self, filename, mode='w', dpmm=12, ):
        assert mode in 'wa', "only write 'w' or append 'a' is supported as mode"
        self.file = open(filename, mode)
        self.dpmm = dpmm
    
    def send_job(self, zpl2):
        self.file.write(zpl2)
    
    def __del__(self):
        self.file.close()

class UDPPrinter(Printer):
    # TODO
    pass