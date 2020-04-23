#!/usr/bin/env python

from __future__ import division
from __future__ import print_function

import socket
import re
import logging
import os
import sys

log = logging.getLogger(__name__)

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

    def get_printer_errors(self):
        if not self._info:
            ret = self.request_info('~HQES').decode('utf-8').strip().split('\n')

            warning = ret[4].strip()[-19:].split()
            descr_warning = []

            bit = int(warning[1][5:6])
            if bit & 1:
                descr_warning.append('Sensor 5 (presenter)')
            elif bit & 2:
                descr_warning.append('Sensor 6 (retract ready)')
            elif bit & 4:
                descr_warning.append('Sensor 7 (in retract)')
            elif bit & 8:
                descr_warning.append('Sensor 8 (at bin)')

            bit = int(warning[1][6:7])
            if bit & 1:
                descr_warning.append('Sensor 1 (Paper before head)')
            elif bit & 2:
                descr_warning.append('Sensor 2 (Black mark)')
            elif bit & 4:
                descr_warning.append('Sensor 3 (Paper after head)')
            elif bit & 8:
                descr_warning.append('Sensor 4 (loop ready)')

            bit = int(warning[1][7:8])
            if bit & 1:
                descr_warning.append('Need to Calibrate Media')
            elif bit & 2:
                descr_warning.append('Clean Printhead')
            elif bit & 4:
                descr_warning.append('Replace Printhead')
            elif bit & 8:
                descr_warning.append('Paper-near-end Sensor')

            error = ret[3].strip()[-19:].split()
            descr_error = []

            bit = int(error[2][3:4])
            if bit & 1:
                descr_error.append('Paused')
            elif bit & 2:
                descr_error.append('Retract Function timed out')
            elif bit & 4:
                descr_error.append('Black Mark Calabrate Error')
            elif bit & 8:
                descr_error.append('Black Mark not Found')

            bit = int(error[2][4:5])
            if bit & 1:
                descr_error.append('Paper Jam during Retract')
            elif bit & 2:
                descr_error.append('Presenter Not Running')
            elif bit & 4:
                descr_error.append('Paper Feed Error')
            elif bit & 8:
                descr_error.append('Clear Paper Path Failed')

            bit = int(error[2][5:6])
            if bit & 1:
                descr_error.append('Invalid Firmware Configuration')
            elif bit & 2:
                descr_error.append('Printhead Thermistor Open')

            bit = int(error[2][6:7])
            if bit & 1:
                descr_error.append('Printhead Over Temperature')
            elif bit & 2:
                descr_error.append('Motor Over Temperature')
            elif bit & 4:
                descr_error.append('Bad Printhead Element')
            elif bit & 8:
                descr_error.append('Printhead Detection Error')

            bit = int(error[2][7:8])
            if bit & 1:
                descr_error.append('Media Out')
            elif bit & 2:
                descr_error.append('Ribbon Out')
            elif bit & 4:
                descr_error.append('Head Open')
            elif bit & 8:
                descr_error.append('Cutter Fault')

        return (warning[0], descr_warning, error[0], descr_error)

    def get_mac(self):
        p = re.compile(r'(?:[0-9a-fA-F]:?){12}')
        ret = self.request_info('~HQHA').decode('utf-8').strip()
        return re.findall(p, ret)[0]

    def get_sn(self):
        ret = self.request_info('~HQSN').decode('utf-8').strip().split('\n')
        return ret[3].strip()

    def get_print_head_test(self):
        ret = self.request_info('~HQJT').decode('utf-8').strip()
        return ret

    def get_maint_current_settings(self):
        ret = self.request_info('~HQMA').decode('utf-8').strip()
        return ret

    def get_print_meters(self):
        ret = self.request_info('~HQOD').decode('utf-8').strip()
        return ret

    def get_printer_info(self):
        if not self._info:
            ret = self.request_info('~HI').decode('utf-8').strip()
            m = re.match('\x02(?P<model>[^,]+),' +
                         r'(?P<version>[^,]+),' +
                         r'(?P<dpmm>[^,]+),' +
                         '(?P<mem>[^,]+)\x03', ret)
            self._info = m.groupdict()

        return self._info

    def get_printer_status(self, reload=False):
        if not self._stat or reload:
            ret = self.request_info('~HS').decode('utf-8').strip().split('\r\n')

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
            ret = self.request_info('^XA^HH^XZ').decode('utf-8').strip('\x02\x03 \t\n\r').split('\r\n')
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
        #return (length, width)
        return length

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
    def __init__(self, host, port=9100, socket_timeout=5):
        try:
            log.debug('Socket create: {}:{}'.format(host, port))
            self.socket = socket.create_connection((host, port), timeout=socket_timeout)
        except socket.timeout:
            log.error('Socket create timeout')
            raise
        except:
            log.exception('Socket create exception: {}'.format(sys.exc_info()[1]))
            raise
        finally:
            log.debug('Socket create finished')
            Printer.__init__(self)

    def send_job(self, zpl2):
        try:
            log.debug('Send: {}'.format(zpl2))
            self.socket.sendall(zpl2.encode('utf-8'))
        except socket.timeout:
            log.error('Send timeout')
            raise
        except:
            log.exception()
            raise
        finally:
            log.debug('Send finished')

    def request_info(self, command):
        try:
            log.debug('Request: {}'.format(command))
            self.socket.sendall(command.encode('utf-8'))

            buf = b""
            while b'\x03' not in buf:
                buf += self.socket.recv(4096)

            log.debug('Request returned: {}'.format(
                buf.decode('utf-8').strip('\x02\x03\t\n\r').replace('  ','')))
            return buf
        except socket.timeout:
            log.error('Send timeout')
            raise
        except:
            log.exception()
            raise
        finally:
            log.debug('Request finished')

    def __del__(self):
        if 'self.socket' in locals():
            self.socket.close()


class FilePrinter(Printer):
    def __init__(self, filename, mode='w', dpmm=12, ):
        assert mode in 'wa', "only write 'w' or append 'a' is supported as mode"
        self.file = open(filename, mode)
        self.dpmm = dpmm

    def send_job(self, zpl2):
        self.file.write(zpl2)
    
    def send_request(self, command):
        raise NotImplementedError

    def __del__(self):
        self.file.close()


class UDPPrinter(Printer):
    # TODO
    pass
