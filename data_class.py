# Copyright (c) 2015-2016 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>
# Licensed under the Creative Commons Attribution-ShareAlike  3.0 (CC BY-SA 3.0 US) License

""" Data class that will be updated from the USB and then call the graph to be updated
"""
#standard libraries
import array
import datetime
import logging
import os
import pickle
import tkinter as tk
from tkinter import filedialog
# local files
import save_toplevel


__author__ = 'Kyle V. Lopin'

# constants
SAMPLE_RATE = 5000.0  # Hz
MAX_READING_TIME = 200  # s
RATE_TO_DISPLAY = 500.0 # Hz
DISPLAY_BUFFER_SIZE = int(MAX_READING_TIME * RATE_TO_DISPLAY)  # s/s - unitless
SAMPLING_RATIO = int(SAMPLE_RATE / RATE_TO_DISPLAY)

class StreamingData(object):
    def __init__(self):
        self.number_channels = 1
        self.sampling_period = 1.0 / RATE_TO_DISPLAY
        self.end_time = 0
        self.graph = None
        self.save_state = SaveState()
        # self.t_data = array.array('f')
        self.t_data = array.array('f')
        for i in range(DISPLAY_BUFFER_SIZE):
            self.t_data.append(i*self.sampling_period)

        logging.debug('t data: ', self.t_data[0:10])
        self.raw_data_ptr = 0
        self.display_data_ptr = 0
        self.counts_to_volts = 1
        self.voltage_shift = 0
        self.adc_counts = [array.array('h')]
        self.y_data_to_display = [array.array('f', [0] * DISPLAY_BUFFER_SIZE)
                                  for _ in range(self.number_channels)]

        # to save the data use the format of 'AXXYYZZ' where A is a letter, A, B, C..
        # for each branch that is measured, XX is the year, YY is the month and ZZ is the day
        # get the letter and number of file to use to save the next file with
        # date = str(datetime.date.today())
        # date_str = date[2:4] + date[5:7] + date[8:]
        # self.save_state = SaveState(date_str)

    def set_count_to_volts(self, counts_to_volts, voltage_shift):
        self.counts_to_volts = counts_to_volts
        self.voltage_shift = voltage_shift

    def add_display_area(self, graph):
        self.graph = graph

    def extend(self, data):
        """ Take in an array of int16 and add it to the data so far
        :param data:
        :return:
        """
        self.adc_counts.extend(data)
        self.sample_signal(data, SAMPLING_RATIO)

    def display_data(self):
        """ Display the data
        :return:
        """
        self.graph.display_data()

    def sample_signal(self, data_packet, skip):
        _len = len(data_packet)
        number_channels = self.number_channels
        while self.raw_data_ptr < _len:
            for data_to_display in self.y_data_to_display:
                data_to_display[self.display_data_ptr] = (data_packet[self.raw_data_ptr]
                                                          * self.counts_to_volts)
                                                          # + self.voltage_shift)
                self.raw_data_ptr += 1
            self.raw_data_ptr += (skip * number_channels) - number_channels
            self.display_data_ptr += 1

        self.raw_data_ptr -= _len
        # this will give the time that has been read so far
        self.end_time = self.t_data[self.display_data_ptr-1]
        # print('end time: {0}'.format(self.end_time))

    def clear(self):
        self.adc_counts = [array.array('h')]
        self.end_time = 0
        self.raw_data_ptr = 0
        self.display_data_ptr = 0
        self.y_data_to_display = [array.array('f', [0] * DISPLAY_BUFFER_SIZE)
                                  for _ in range(self.number_channels)]
        logging.debug('ydisplay: ', len(self.y_data_to_display))

    def set_number_channels(self, num):
        self.number_channels = num
        self.clear()
        if self.graph:
            self.graph.draw_new_data(self.t_data, self.y_data_to_display)

    def get_time_series(self):
        return self.t_data

    def get_voltage_data(self):
        return self.y_data_to_display

    def call_save(self):
        # SaveTopLevel(self)
        file_opts = {}
        file_opts['initialdir'] = os.getcwd()+'\data\{0}'.format(self.save_state.date_str)
        file_opts['filetypes'] = [("Pickle File", "*.pkl")]
        filename = filedialog.asksaveasfilename(**file_opts)
        filename += '.pkl'
        # print('save as file: {0}'.format(filename))
        # print("len raw data: {0}; number channels: {1}".format(len(self.adc_counts), self.number_channels))
        # print('last adc count: {0}; first adc count: {1}'.format(self.adc_counts[-1], self.adc_counts[0]))
        len_channel = int(len(self.adc_counts) / self.number_channels)
        # print('len channel: {0}'.format(len_channel))
        channel_data = dict()
        for i in range(self.number_channels):
            channel_data["channel {0}".format(i)] = array.array('h')
        data_ptr = 1
        # print('channel data: {0}'.format(channel_data))
        for i in range(len_channel-1):
            for j in range(self.number_channels):
                # print('j: {0}; i: {1}; data_ptr: {2}'.format(j, i, data_ptr))
                channel_data["channel {0}".format(j)].append(self.adc_counts[data_ptr])
                data_ptr += 1
        # for ch in channel_data:
            # print(channel_data[ch])
        data_struct = dict()
        data_struct['sample rate'] = SAMPLE_RATE
        data_struct['counts to mVs'] = self.counts_to_volts
        for _data_ch in channel_data:
            data_struct[_data_ch] = channel_data[_data_ch]

        with open(filename, 'wb') as f:
            pickle.dump(data_struct, f, pickle.HIGHEST_PROTOCOL)


class SaveTopLevel(tk.Toplevel):
    def __init__(self, data_parent: StreamingData):
        tk.Toplevel.__init__(self, master=None)
        self.geometry('400x300')
        self.title("Save data")
        self.data_was_saved = False

        # make file name string
        self.save_state = SaveState()
        num_str = str(self.save_state.file_number).zfill(3)

        self.filename_str = self.save_state.branch + self.save_state.date_str + '_' + num_str
        print('filename string: {0}'.format(self.filename_str))
        # make frame to make a generic name to suggest to the user
        filename_frame = tk.Frame(self)
        filename_frame.pack(side='top')
        tk.Label(filename_frame, text="File name to save as: ").pack(side='left')
        self._filename_var = tk.StringVar()
        self._filename_var.trace("w", self.update_filename)
        self.filename_entry = tk.Entry(filename_frame, textvariable=self._filename_var)
        # get the filename the should be used
        fill_in_filename(self.filename_entry, self.filename_str)
        self.filename_entry.pack(side='left')

        # make spinbox to label which branch was recorded
        branch_frame = tk.Frame(self)
        branch_frame.pack(side='top')
        tk.Label(branch_frame, text="Branch letter: ").pack(side='left')
        _branch_var = tk.StringVar()
        _branch_var.set(self.save_state.branch)
        branch_spinbox = tk.Spinbox(branch_frame, width=6,
                                    values=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
                                    command=lambda: self.branch_change(branch_spinbox.get()))
        branch_spinbox.delete(0, "end")
        branch_spinbox.insert(0, self.save_state.branch)
        branch_spinbox.pack(side='left')

        # make save and cancel buttons
        button_frame = tk.Frame(self)
        button_frame.pack(side='bottom')
        tk.Button(button_frame, text="Save File", command=data_parent.save
                  ).pack(side='left', padx=20)
        tk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='left', padx=20)

    def update_filename(self, *args):
        self.filename_str = self._filename_var.get()

    def branch_change(self, value: str):
        """ Change the branch letter to save the data as.
        Update the save_branch variable, and make a new filename to display to the user
        :param value: char, new letter
        :param save_state: SaveState, object to save recording info
        """
        self.save_state.branch = value
        self.filename_str = value + self.filename_str[1:]
        fill_in_filename(self.filename_entry, self.filename_str)


class SaveState(object):
    """ Class to keep track of the date of the experiment, the letter of the branch
     being recorded, and the recording number """
    def __init__(self):
        # check for a save state file first
        date = str(datetime.date.today())
        self.date_str = date[2:4] + date[5:7] + date[8:]
        try:
            state_data = shelve.open('state.db')
            if state_data['date'] == self.date_str:
                self.branch = state_data['branch']
                self.file_number = state_data['file number']
                return
        except:
            pass
        self.branch = 'A'
        self.file_number = 1


def fill_in_filename(_entry, filename):
    _entry.delete(0, "end")
    _entry.insert(0, filename)
