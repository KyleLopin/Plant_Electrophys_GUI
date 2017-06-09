# Copyright (c) 2015-2017 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>
# Licensed under the Creative Commons Attribution-ShareAlike  3.0 (CC BY-SA 3.0 US) License

""" Communicate with a USB device for a data acquisition system
"""
# standard libraries
import array
import ctypes
import logging
import os
import queue
import shelve
import threading
import time

# installed libraries
import usb.core
import usb.util
import usb.backend
# import usb_mock as usb

# local files
from usb_constants import *

__author__ = 'Kyle V. Lopin'


REFRESH_DELAY = 200  # type: int    mseconds to delay updating plot after it has been updated, give some time to the other threads


class PlantUSB(object):
    """ Class to communicate with a device that can measure a number of different input signals, receives the raw
    adc counts from the device and converts the adc counts to the voltage measured.   Supports a calibration routine
    (NOTE: This also has to be supported in the hardware) that is used to calculate the conversion factor of 
    adc counts to millivolts
    
    A seperate thread, ThreadedUSBDATA will handle all the data collection details and put the raw uint16 adc counts
    of all adc channels into data_queue.  All data processing will be done in the data class which is running on
     the main  thread.
    
    The device updates the data_class and data_class converts the data, samples the data and updates the display
    
    Constants used in this are found in usb_constants.py
    """

    def __init__(self, master, vendor_id=0x04B4, product_id=0x8051):
        """ Bind objects, initialize other threads to be used and check if the device has been calibrated recently
        :param master: root tk.Tk()
        :param vendor_id: hexadecimal of USB's vendor id
        :param product_id: hexadecimal of USB's product id
        """
        print('check1')
        self.channel_tracker = 0
        self.master = master  # type: tk.Tk
        self.data = master.data  # type: data_class.StreamingData
        self._device = self.connect_usb(vendor_id, product_id)  # Type: pyUSB device
        self.data_queue = queue.Queue()  # This will store all the raw adc counts of an adc channel, i.e. as many data
        # points as is stored in DC_CHANNEL_DATA_SIZE
        self.packet_ready_event = threading.Event()
        # Placeholder for now, make a new thread everytime a data stream is started
        self.threaded_data_stream = None  # type: threading.thread
        # check if a usb settings file exists
        print('check2', os.getcwd())
        print(os.path.exists('usb_settings.db'))
        print(os.path.isfile('usb_settings.db'))
        with shelve.open('usb_settings.db') as settings:
            if settings:
                self.gain = settings['gain']
                self.zero_level = settings['zero level']
                settings.close()
            else:
                self.gain = 1
                self.zero_level = 0
                print("NEED TO CALIBRATE")
        self.number_channels = 1
        self.counts_to_volts = float(MAX_ADC_VOLTAGE) / MAX_ADC_COUNTS / self.gain  # TODO: is this needed or just pass it to data
        logging.info('starting voltge to count: {0}'.format(self.counts_to_volts))
        # TODO:  delete below to get correct number and fix this part over all
        self.data.set_count_to_volts(self.counts_to_volts, self.zero_level)

        if self._device:  # the device has been found, make sure it response to information requests properly
            self.connected = self.connection_test()

    def connect_usb(self, _vendor_id=0x04B4, _product_id=0xE177):
        """ Use the pyUSB module to find and set the configuration of a USB device

        This method uses the pyUSB module, see the tutorial example at:
        https://github.com/walac/pyusb/blob/master/docs/tutorial.rst
        for more details

        :param _vendor_id:  the USB vendor id, used to identify the proper device connected to
        sthe computer
        :param _product_id: the USB product id
        :return: USB device that can use the pyUSB API if found, else returns None if not found
        """
        device = usb.core.find(idVendor=_vendor_id, idProduct=_product_id)
        # if no device is found, print a warning to the output
        if device is None:
            logging.info("Device not found")
            return None
        else:  # device was found
            logging.info("USB device is found")

        # set the active configuration. the pyUSB module deals with the details
        device.set_configuration()
        return device

    def connection_test(self):
        """ Test if the device response correctly.  The device should return a message when
        given and identification call of "I"
        :return: True or False if the device is communicating correctly
        """
        # clear the IN BUFFER of the device incase it was stopped or the program was restarted
        self.clear_in_buffer()
        # needed to make usb_write work, will be updated if not connected correctly
        self.connected = True
        self.usb_write("I")  # device should identify itself
        received_message = self.usb_read_data(encoding='string')
        logging.debug('Received identifying message: {0}'.format(received_message))
        if received_message == RECIEVED_TEST_MESSAGE:
            logging.info("Device identified")
            self.working = True  # for usb_write to work it needs the working property to be true
            return True
        else:
            logging.info("Identification Failed")
            return False

    def usb_write(self, message, endpoint=OUT_ENDPOINT):
        """ Write a message to the device
        :param message: message, in bytes, to send
        :param endpoint: which OUT_ENDPOINT to use to send the message in the case there are more
        than 1 OUT_ENDPOINTS
        :return:
        """
        if not self.connected:
            logging.info("Device not connected")
        elif len(message) > 32:
            logging.error("Message is too long")
        else:
            logging.debug("writing message: %s", message)
            try:
                self._device.write(endpoint, message)
            except Exception as error:
                logging.error("No OUT ENDPOINT: %s", error)
                self.connected = False

    def usb_read_info(self, endpoint=INFO_IN_ENDPOINT, num_usb_bytes=USB_INFO_BYTES_SIZE):
        """ Read the information endpoint of the device and return it as a string if the device responded, else
        log the failed read and return None
        :param endpoint:  hexidecimal of endpoint to read, has to be formatted as 0x8n where 
        n is the hex of the encpoint number
        :param num_usb_bytes: how many bytes to read from the device
        :return: string of information from the device if it responded, else None if not
        """
        if not self.connected:
            logging.info("not working")
            return None
        try:
            usb_input = self._device.read(endpoint, num_usb_bytes)  # type: array.array('b')
            return usb_input.tostring()  # return message after converting to a string
        except Exception as error:
            logging.info("Failed read")
            logging.info("No IN ENDPOINT: %s", error)
            return None
# TODO remove usb_read_info and replace with usb_read_data with proper endpoint and num bytes, encode = 'String
    def usb_read_data(self, num_usb_bytes=USB_DATA_BYTE_SIZE, endpoint=DATA_STREAM_ENDPOINT, encoding=None):
        """ Read data from the usb and return it, if the read fails, log the miss and return None
        :param num_usb_bytes: number of bytes to read
        :param endpoint: hexidecimal of endpoint to read, has to be formatted as 0x8n where 
        n is the hex of the encpoint number
        :param encoding: string ['uint16', 'signed int16', or 'string] what data format to return
        the usb data in
        :return: array of the bytes read
        """
        if not self.connected:
            logging.info("not working")
            return None
        try:
            usb_input = self._device.read(endpoint, num_usb_bytes)  # TODO fix this

        except Exception as error:
            logging.error("Failed data read")
            logging.error("No IN ENDPOINT: %s", error)
            return None
        if encoding == 'uint16':
            return convert_uint8_uint16(usb_input)
        elif encoding == "signed int16":
            return convert_uint8_to_signed_int16(usb_input)
        elif encoding == 'string':
            return usb_input.tostring()  # remove the 0x00 end of string
        else:  # no encoding so just return raw data
            return usb_input

    def start_reading(self):
        """ Read a stream of data in a seperate thread.  Clears any previeous data queues, send the start message to 
        the device, start data reading thread and start data processing loop
        """
        while self.data_queue.qsize():  # clear the data queue of any previously added data
            _ = self.data_queue.get(0)
        # moved
        # self.threaded_data_stream = ThreadedUSBDataCollector(self, self.data_queue)
        self.usb_write('R')  # signal for the device to start
        self.threaded_data_stream = ThreadedUSBDataCollector(self, self.number_channels,
                                                             self.data_queue,
                                                             self.packet_ready_event)
        self.threaded_data_stream.start()  # thread to handle the I/O
        self.process_data_stream()  # reads data from data_queue and

    def process_data_stream(self):
        """ Wait for the data azquisition thread the laod a packet, then load it into the data class and recall this
        method
        """
        # print('data queu size = {0}'.format(self.data_queue.qsize()))
        data_added = False
        # wait for the data acquisition thread to signal an adc channel has been loaded
        self.packet_ready_event.wait()
        self.packet_ready_event.clear()
        while self.data_queue.qsize():
            try:
                self.data.extend(self.data_queue.get(0))
                data_added = True
                # print('data in queu: {0}'.format(data))
                # voltage = self.convert_data(data)
                # logging.debug('data: {0}'.format(data))

            except queue.Empty:
                pass  # should not happen
        if data_added:
            self.data.display_data()
        self.display_loop = self.master.after(200, self.process_data_stream)

    # def convert_data(self, adc_counts):
    #     # logging.debug('processing data: {0}'.format(adc_counts))
    #     voltage = array.array('f', [self.counts_to_volts * adc_count for adc_count in adc_counts])
    #     return voltage

    def stop_reading(self):
        if hasattr(self, 'threaded_data_stream'):  #TODO: This dont work any more, find a new way to tell if there the device is not running
            self.threaded_data_stream.stop_running()
            # empty the data queue
            self.master.after_cancel(self.display_loop)

    def clear_in_buffer(self):
        pass

    def set_number_channels(self, num_channels: int):
        logging.debug('setting channels to: {0}'.format(num_channels))
        self.number_channels = num_channels
        self.usb_write('S{0}'.format(num_channels))
        self.data.set_number_channels(num_channels)

    def set_offset_vdac(self, _settings):
        logging.debug('sending voltage: ', _settings)
        _settings = int(_settings)

        self.usb_write('V{0:0>4}'.format(_settings))

    def calibrate(self):
        # get 3 seconds of data
        self.data.clear()
        self.start_reading()
        self.after(4000, self._device.stop_reading)
        self.after(4100, self.calibrate_finish)
        self._device.send_message('C')

    def calibrate_finish(self):
        self.master.calibrate_finish()  # will reenable the buttons
        self.process_calibration_data(self.data)

    def process_calibration_data(self, data):
        # dump the first 500 msec of data to let the calibration cycle start
        # and the amplifiers to settle
        voltage_data = data.get_voltage_data()[5000:]
        mean_voltage = sum(voltage_data) / len(voltage_data)
        upper_level = [i for i in voltage_data if i > mean_voltage]
        lower_level = [i for i in voltage_data if i < mean_voltage]
        upper_level_mean = sum(upper_level) / len(upper_level)
        lower_level_mean = sum(lower_level) / len(lower_level)
        print('upper level mean = ', upper_level_mean)
        print('lower level mean = ', lower_level_mean)

        self.counts_to_volts /= (upper_level_mean - lower_level_mean) / \
                                CALIBRATION_RANGE  # counts per mV change in signal
        voltage_difference = upper_level_mean - lower_level_mean

        if CALIBRATION_RANGE - 0.5 < voltage_difference < CALIBRATION_RANGE + 0.5:
            print('Passed Calibration')
        else:
            print('======================= CALIBRATION FAIL ==============================')
            print('Check calibration again')
        print('gain = ', self.counts_to_volts)

        self.zero_level -= lower_level_mean
        settings = shelve.open('usb_settings.db')
        settings['gain'] = self.counts_to_volts
        settings['zero level'] = self.zero_level
        self.data.set_count_to_volts(self.counts_to_volts, self.zero_level)


class ThreadedUSBDataCollector(threading.Thread):
    """ Seperate thread to collect the adc channel packets from the device.  This starts another thread that 
    handles the timing of when to get what adc channel.
    """

    def __init__(self, device, number_adc_channels: int,
                 data_queue: queue.Queue, data_event: threading.Event):
        self.channel_tracker = 0
        self.read_count = 0  # for debug
        threading.Thread.__init__(self)
        self.device = device
        self.number_adc_channels = number_adc_channels
        self.data_queue = data_queue  # queue to put the adc packets in
        self.data_done = data_event  # event to signal the main thread the data is ready
        self.adc_channel_queue = queue.Queue()  # queue the sepereate thread uses to tell this thread when to collect
        # an adc channel
        self.adc_channel_ready_event = threading.Event()  # event to signal an adc channel is ready to export its data
        self.running = True
        self.termination_flag = False
        # make another thread to read the information endpoint of the device what will signal when an adc channel is
        # ready to export its data and what channel it is
        self.info_thread = ThreadedUSBInfo(device, self.adc_channel_queue,
                                           self.adc_channel_ready_event)

    def run(self):
        """ Start the information thread and then call the data read method that will get the adc packets
        """
        self.info_thread.start()
        self.data_read()

    def data_read(self):
        """ Wait for the information thread to set the adc_channel_ready_event flag 
        then get an adc packet from the device
        """
        while not self.termination_flag:
            # wait till the device has send the signal that an adc channel is done
            self.read_count += 1
            # print('read count: {0}'.format(self.read_count))
            self.adc_channel_ready_event.wait()
            self.adc_channel_ready_event.clear()
            if not self.adc_channel_queue.empty():  # make sure the adc channel is ready to import
                # logging.info('channel size: {0}'.format(self.adc_channel_queue.qsize()))
                if self.adc_channel_queue.qsize() != 1:
                    logging.debug("====== qsize: {0}".format(self.adc_channel_queue.qsize()))
                    # raise Exception
                # tell the device to send the data
                hold = self.adc_channel_queue.get()
                logging.debug('channel tracker: {0}, channel expected{1}'
                              .format(self.channel_tracker, hold))
                if int(hold) != self.channel_tracker:
                    logging.debug('channel tracker: {0}, expected: {1}'
                                  .format(self.channel_tracker, hold))
                self.channel_tracker += 1
                self.channel_tracker %= 4
                if self.running:
                    self.device.usb_write('F{0}'.format(hold))  # 'F#' is device symbol to export # adc channel
                    # read the adc channel data
                    self.get_adc_buffer(number_packets=PACKETS_PER_CHANNEL)
                else:  # dont request an ADC channel if read should be stopped, just send termination code to device
                    self.device.usb_write('E')  # 'E' is device symbol to stop the data reading
                    self.termination_flag = True  # Stop the thread from running
            # else there is no adc channel ready which should not happen

        return 0

    def get_adc_buffer(self, endpoint=DATA_STREAM_ENDPOINT, number_packets=1):
        """ Read an adc buffer from the device.
        :param endpoint: device endpoint to read, NOTE: the read endpoint needs to be format as
        0x8n where n is the endpoint point number
        :param number_packets: int, how many usb packet to read
        """
        # logging.debug('getting adc channel with {0} inputs'.format(self.number_adc_channels))
        packets_gotten = 0  # keep track of haw many packets have been retrieved
        full_array = array.array('h')  # array to store data
        # logging.debug('getting buffer')
        while number_packets + 1 > packets_gotten:
            # logging.debug('getting packet: {0}; len = {1}'.format(packets_gotten, len(full_array)))
            data_packet = self.data_try(endpoint=endpoint)  # try to get a packet
            # logging.info('full array len: {0}; {1}'.format(len(full_array), len(data_packet)))
            if not data_packet:
                return

            full_array.extend(data_packet)  # add data to array
            # the device should put a termination code at the end of the adc channel
            if full_array[-1] == TERMINATION_CODE:
                full_array.pop()  # remove the termination code and exit loop
                break
            # if len(full_array) == 2040:
            #     break
            packets_gotten += 1
        self.data_queue.put(full_array)
        self.data_done.set()  # set adc channel loaded flag

    def data_try(self, endpoint=DATA_STREAM_ENDPOINT):
        try:
            usb_input = self.device.usb_read_data(endpoint=endpoint)
            return convert_uint8_to_signed_int16(usb_input)

        except Exception as e:
            print('failed in data_try: ', e)

    def stop_running(self):
        """ Set flags that tell this tread and the information thread to stop """
        self.running = False
        self.info_thread.stop_running()
        #TODO: empty the queue don't start a new one, see if this worked
        time.sleep(0.1)  # wait for the threads to stop before clearing queues
        while self.adc_channel_queue.qsize():
            _ = self.adc_channel_queue.get()


class ThreadedUSBInfo(threading.Thread):
    """ Thread that will check the information endpoint for signals that the deivce has set the event that
    signals an adc channel is ready to be exported
    """

    def __init__(self, device: PlantUSB, adc_queue: queue.Queue,
                 adc_channel_event: threading.Event):
        threading.Thread.__init__(self)
        self.device = device
        self.adc_queue = adc_queue
        self.adc_event = adc_channel_event
        self.running = True  # bool: Flag to know when the data read should stop
        self.termination_flag = False  # Flag to know when the thread should stop

    def run(self):
        """ Poll the information endpoint for a response, should respond with a 'Done#, where #
        is the adc buffer  in the device that is ready to be exported.  Currently it ignores the
        'Done' part because that is the only message the device currently uses for the information
        endpoint.
        """
        while not self.termination_flag:
            # logging.debug('reading info')
            if self.running:
                # check if an adc channel has been finished by looking at the INFO_ENDPOINT,
                # the timeout is long enough that this should hold here til the device responds
                message = self.device.usb_read_info()
                logging.debug('got message: {0}'.format(message))
                if message:
                    self.adc_queue.put(chr(message[4]))  # put what channel the device should get
                    self.adc_event.set()  # set flag so ThreadedUSBDataCollector knows to get the adc buffer channel
                    logging.debug('got info: {0}'.format(message))
                    # logging.debug('self.running: {0}'.format(self.running))
            else:
                self.termination_flag = True
        # logging.debug('Ending info thread')
        return 0

    def stop_running(self):
        """ set running flag to false so the next run will be the last.  Use run one more time to clear the 
        Endpoint buffer.  TODO; Is this necessary?
        """
        logging.debug('stopping the info thread')
        self.running = False


def convert_uint8_uint16(_array):
    """ Convert an array of uint8 to uint16
    :param _array: list of uint8 array of data to convert
    :return: list of uint16 converted data
    """
    #TODO use like the converst to signed int
    new_array = [0]*(len(_array)/2)
    for i in range(len(_array)/2):
        _hold = _array.pop(0) + _array.pop(0) * 256
        if _hold == USB_TERMINATION_SIGNAL:
            new_array[i] = _hold
            break
        new_array[i] = _hold
    return new_array


def convert_uint8_to_signed_int16(_bytes):
    """ Convert an array of bytes into an array of signed int16
    :param _bytes: array of uint8
    :return: array of signed int16
    """
    """  below takes 7 msecs
    length = int(len(_bytes) / 2)
    hold = (ctypes.c_short * length).from_buffer_copy(_bytes)
    return list(hold)
    """
    # below takes 6-11msec
    length = int(len(_bytes) / 2)
    return array.array('h', (ctypes.c_short * length).from_buffer_copy(_bytes))



def convert_uint8_to_string(_bytes):
    """ Convert bytes to a string
    :param _bytes: list of bytes
    :return: string
    """
    # TODO: use tostring()
    i = 0
    _string = ""
    while _bytes[i] != 0:
        _string += chr(_bytes[i])
        i += 1
    return _string
