#!/usr/bin/env python

from __future__ import division
from __future__ import print_function

import socket
import re

class Printer:
    '''
    This abstract Printer class is used to interface with ZPL2 printers.
    '''
    def __init__(self):
        self._info = {}
        self._cfg = {}
        self._stat = {}
    
    def send_job(self, zpl2):
        print(zpl2)
    
    def request_info(self, command):
        raise Exception("not implemented in this printer class")
    
    def get_printer_info(self):
        if not self._info:
            ret = self.request_info('~HI').strip()
            m = re.match('\x02(?P<model>[^,]+),' +
                         r'(?P<version>[^,]+),' +
                         r'(?P<dpmm>[^,]+),' +
                         '(?P<mem>[^,]+)\x03', ret)
            self._info = m.groupdict()
        
        return self._info
    
    def get_printer_status(self, reload=False):
        if not self._stat or reload:
            ret = self.request_info('~HS').strip().split('\r\n')
            m = re.match('\x02(?P<interface>[^,]+),' +
                         r'(?P<paper_out>[^,]+),' +
                         r'(?P<pause>[^,]+),' +
                         r'(?P<label_length>[^,]+),' +
                         r'(?P<number_of_formats_in_recv_buf>[^,]+),' +
                         r'(?P<buffer_full>[^,]+),' +
                         r'(?P<comm_diag_mode>[^,]+),' +
                         r'(?P<partial_format>[^,]+),' +
                         r'000,' +
                         r'(?P<corrupt_ram>[^,]+),' +
                         r'(?P<under_temp>[^,]+),' +
                         '(?P<over_temp>[^,]+)\x03', ret[0])
            self._stat.update(m.groupdict())
            print(ret[1].__repr__())
            m = re.match('\x02(?P<func_settings>[^,]+),' +
                         r'[^,]+,' +  # unused
                         r'(?P<head_up>[^,]+),' +
                         r'(?P<ribbon_out>[^,]+),' +
                         r'(?P<thermoal_transfer>[^,]+),' +
                         r'(?P<print_mode>[^,]+),' +
                         r'(?P<print_width_mode>[^,]+),' +
                         r'(?P<label_waiting>[^,]+),' +
                         r'(?P<labels_remaining>[^,]+),' +
                         r'(?P<format_while_printing>[^,]+),' +
                         '(?P<graphics_stored_in_mem>[^,]+)\x03', ret[1])
            self._stat.update(m.groupdict())
            m = re.match('\x02(?P<password>[^,]+),' +
                         '(?P<static_ram>[^,]+)\x03', ret[2])
            self._stat.update(m.groupdict())
        
        return self._stat
    
    def get_printer_config(self, reload=False):
        if not self._cfg or reload:
            ret = self.request_info('^XA^HH^XZ').strip('\x02\x03 \t\n\r').split('\r\n')
            for l in ret:
                l = l.strip()
                
                # find longest space-streak
                i = j = 0
                k = 1
                while j != -1:
                    i = j
                    j = l.find(' '*k, j)
                    k += 1
                self._cfg[l[i:].strip()] = l[:i].strip()
        
        return self._cfg
    
    def get_label_dimensions(self):
        length = int(self.get_printer_status()['label_length'])//self.get_dpmm()
        return (length, width)
    
    def get_dpi(self):
        '''returns dots per inch of printer.'''
        return self.get_dpmm()*25
    
    def get_dpmm(self):
        '''returns dots per millimeter of printer.'''
        return int(self.get_printer_info()['dpmm'])
        

class TCPPrinter(Printer):
    '''
    This class allows to interface with a ZPL2 printer via a TCP port.
    '''
    
    def __init__(self, host, port=9100):
        self.socket = socket.create_connection((host, port))
        Printer.__init__(self)
    
    def send_job(self, zpl2):
        self.socket.sendall(zpl2)
    
    def request_info(self, command):
        self.socket.sendall(command)
        buf = ""
        while '\x03' not in buf:
            buf += self.socket.recv(4096)
        return buf
    
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