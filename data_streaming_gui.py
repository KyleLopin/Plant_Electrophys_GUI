# Copyright (c) 2015-2017 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>
# Licensed under the Creative Commons Attribution-ShareAlike  3.0 (CC BY-SA 3.0 US) License

""" Graphical User Interface to communicate with a Programmable System on a Chip device that can 
read up to 4 adc channels at a time and display it to the user.  Because this project is for recording plant
electrical activity at a high sampling rate, the data displayed is down sampled and the data structure is 
optimized to store large amounts of data and separate threads to retrieve the USB data
"""

# standard libraries
import array
import datetime
import logging
import os
import time
import tkinter as tk
# installed libraries
#local files
import data_class
import plotter
import usb_comm


__author__ = 'Kyle Vitautas Lopin'

sample_rate = 10000  # Hz
sample_period = 1. / sample_rate  # seconds
gain_list = (1, 2, 4, 8)

class DataStreamingViewer(tk.Tk):
    """ GUI to display the data from adc readings from a USB device.  This program should interact with the 
    device mainly with the usb device and the usb_comm file will deal with the data and how its displayed.
    Exceptions to this are saving the data and opening the data where this class will directly call the data class
    """
    def __init__(self, parent=None):
        tk.Tk.__init__(self, parent)
        logging.basicConfig(format='%(asctime)s %(module)s %(lineno)d: %(levelname)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
        # initialize the custom data class to hold the data and the device
        self.data = data_class.StreamingData()
        self.device = usb_comm.PlantUSB(self)
        # initialize variables
        self.running_job = None
        self.display_time_frame = 5  # type: int
        self.vdac_setting = 500  # type: int mV
        self.gain = 1.0  # type: float
        self.data_saved = True  # type: bool
        # initialize tk Variables
        self.time_var = tk.IntVar()
        self.vdac_var = tk.IntVar()
        self.gain_var = tk.IntVar()

        # make directory and start logging file
        date = str(datetime.date.today())
        date_str = date[2:4] + date[5:7] + date[8:]
        self.data_logging_handler(date_str)
        # make frame for user to select number of adc channels to record
        control_frame = tk.Frame(self)
        self.create_control_panel(control_frame)

        # choose how many seconds to display
        # time_frame = tk.Frame(self)
        self.create_time_frame(control_frame)
        control_frame.pack(side='top')
        offset_frame = tk.Frame(self)
        self.create_offset_frame(offset_frame)
        self.create_gain_frame(offset_frame)
        offset_frame.pack(side='top')

        button_frame1 = tk.Frame(self)
        button_frame1.pack(side='top')
        self.read_button = tk.Button(button_frame1, text="Read", command=self.start_reading)
        self.read_button.pack(side='left')
        self.stop_button = tk.Button(button_frame1, text="Stop", command=self.cancel_read)
        self.stop_button.pack(side='left')
        self.clear_button = tk.Button(button_frame1, text='Clear Data', command=self.data.clear)
        self.clear_button.pack(side='left')
        self.calibrate_button = tk.Button(button_frame1, text='Calibrate', command=self.calibrate)
        # self.calibrate_button.pack(side='left')

        self.data_plot = plotter.Plotter(self, self.data)
        self.data_plot.pack(side='top', fill=tk.BOTH, expand=True)
        self.data.add_display_area(self.data_plot)
        tk.Button(self, text='Save all data', command=self.save_data).pack(side='top')

    def save_data(self):
        # self.data_saved = save_toplevel.SaveTopLevel(self, self.data.x_data, self.data.y_data_to_display)
        self.data.call_save()

    def create_time_frame(self, _frame):
        tk.Label(_frame, text="Seconds to display: ").pack(side='left')
        self.time_var.set(self.display_time_frame)
        tk.Spinbox(_frame, from_=1, to=30, textvariable=self.time_var, width=6).pack(side='left')
        self.time_var.trace("w", self.set_time)

    def create_offset_frame(self, _frame):
        tk.Label(_frame, text="Vref offset (mV): ").pack(side='left')
        self.vdac_var.set(self.vdac_setting)
        tk.Spinbox(_frame, from_=0, to=1024, increment=4, textvariable=self.vdac_var, width=6
                   ).pack(side='left')
        self.vdac_var.trace("w", self.set_offset_vdac)

    def create_gain_frame(self, _frame):
        tk.Label(_frame, text="Set gain: ").pack(side='left')
        self.gain_var.set(self.gain)
        tk.Spinbox(_frame, values=gain_list, textvariable=self.gain_var, width=6).pack(side='left')
        self.gain_var.trace("w", self.set_gain)

    def create_control_panel(self, _frame):
        tk.Label(_frame, text="ADC channels from device: ").pack(side="left")
        channels_var = tk.IntVar()
        channels_var.trace("w", lambda name, index, mode,
                                       sv=channels_var: self.set_channels(channels_var.get()))
        tk.Spinbox(_frame, from_=1, to=3, textvariable=channels_var, width=6).pack(side='left')

    def set_time(self, *args):
        self.display_time_frame = self.time_var.get()
        self.data_plot.set_time_frame(self.display_time_frame)
        # call plotter.display_data if the stream is not running
        # print('+++++++++++++++++++++', self.read_button['state'])
        if self.read_button['state'] == 'active':
            # self.data_plot.draw_new_data(self.x_data, self.y_data, self.display_time_frame)
            self.data_plot.display_data()
        # else the plot will update next time data is updated

    def start_reading(self):
        self.data.clear()

        # disable the run and calibrate buttons to prevent their use
        self.read_button.config(state='disabled')
        self.calibrate_button.config(state='disabled')
        self.device.start_reading()

    def set_channels(self, *args):
        self.device.set_number_channels(args[0])

    def set_gain(self, *args):
        self.gain = self.gain_var.get()
        print('gain = ', self.gain)
        print('send value: ', gain_list.index(self.gain))
        self.device.set_gain(self.gain)

    def set_offset_vdac(self, *args):
        try:
            self.vdac_setting = self.vdac_var.get()
            self.device.set_offset_vdac(self.vdac_setting/4)
        except Exception as e:  # if the user is entering a number it might get messed
            logging.error("Setting Voffset error: {0}".format(e))

    def start_reading_data22(self):
        """ Start reading the data streaming from the device.  Start a new thread to read the
        USB input stream and let the main thread update the graphical display ~ 5 times a second
        :return:
        """
        self.data.clear()
        self.device.start_reading()  # initialize the device to start reading
        logging.info("Reading data from %d channels" % self.data.number_channels)

    def read_data22(self):
        new_data = self.device.get_data(self.channels)
        self.process_data(new_data)
        self.data_plot.draw_new_data(self.x_data, self.y_data, self.display_time_frame)
        self.running_job = self.after(100, self.read_data)

    def update_data22(self):
        new_data = self.device.get_data(self.channels)
        self.process_data(new_data)

    def process_data22(self, raw_data):
        raw_data = list(raw_data)
        while raw_data:
            self.y_data[self.y_data_ptr].append(raw_data.pop(0))
            self.y_data_ptr += 1
            self.y_data_ptr %= self.channels

            if self.y_data_ptr == 0:
                self.x_data.append(self.x_data[-1]+sample_period)

    def cancel_read(self):
        self.device.stop_reading()
        self.read_button.config(state='active')
        self.calibrate_button.config(state='active')

    def data_logging_handler(self, date):
        path = os.getcwd()
        _log_path = '%s/data/%s' % (path, date)
        _log_file = '%s/data/%s/%s.log' % (path, date, date)
        self.make_data_path(_log_path)
        # print('wtf', getattr(logging, loglevel.upper()))
        # print(logging.getEffectiveLevel())
        # logging.basicConfig(format='%(asctime)s %(module)s %(lineno)d: %(message)s',
        #                     datefmt='%m/%d/%Y %I:%M:%S %p',
        #                     filename=_log_file, filemode='a', level=logging.DEBUG)
        # print('wtf', getattr(logging, loglevel.upper()))

    def make_data_path(self, _path):
        # check if '/data' file already exists in current
        if not os.path.exists(_path):
            logging.debug('making data path: ', _path)
            os.makedirs(_path)
        else:  # the program has run today already, get the last used branch letter and file number
            pass
            # self.save_state = 1  # fix this

    def disable_buttons(self):
        for button in [self.calibrate_button, self.clear_button, self.read_button, self.stop_button]:
            button.config(state='disabled')

    def enable_buttons(self):
        for button in [self.calibrate_button, self.clear_button, self.read_button, self.stop_button]:
            button.config(state='normal')

    def calibrate(self):
        # get 3 seconds of data
        self.disable_buttons()
        self.device.calibrate()

    def calibrate_finish(self):
        self.enable_buttons()


if __name__ == '__main__':
    app = DataStreamingViewer()
    app.title("View Data")
    app.geometry("500x450")
    app.mainloop()
