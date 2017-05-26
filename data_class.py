# Copyright (c) 2015-2016 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>
# Licensed under the Creative Commons Attribution-ShareAlike  3.0 (CC BY-SA 3.0 US) License

""" Data class that will be updated from the USB and then call the graph to be updated
"""
#standard libraries
import array
import logging


__author__ = 'Kyle V. Lopin'

# constants
SAMPLE_RATE = 10000.0  # Hz
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
        # self.t_data = array.array('f')
        self.t_data = array.array('f')
        for i in range(DISPLAY_BUFFER_SIZE):
            self.t_data.append(i*self.sampling_period)

        print('t data: ', self.t_data[0:10])
        self.raw_data_ptr = 0
        self.display_data_ptr = 0
        self.counts_to_volts = 1
        self.voltage_shift = 0
        self.adc_counts = [array.array('h') for _ in range(self.number_channels)]
        self.y_data_to_display = [array.array('f', [0] * DISPLAY_BUFFER_SIZE)
                                  for _ in range(self.number_channels)]

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
        while self.raw_data_ptr < _len:
            # assume only 1 channel now and expand to multiple channels later
            self.y_data_to_display[0][self.display_data_ptr] = (data_packet[self.raw_data_ptr]
                                                                * self.counts_to_volts
                                                                + self.voltage_shift)
            self.raw_data_ptr += skip
            self.display_data_ptr += 1
        self.raw_data_ptr -= _len
        # this will give the time that has been read so far
        self.end_time = self.t_data[self.display_data_ptr-1]

    def clear(self):
        self.end_time = 0
        self.raw_data_ptr = 0
        self.display_data_ptr = 0
        self.y_data_to_display = [array.array('f', [0] * DISPLAY_BUFFER_SIZE)
                                  for _ in range(self.number_channels)]
        if self.graph:
            self.display_data()

    def get_time_series(self):
        return self.t_data

    def get_voltage_data(self):
        return self.y_data_to_display

    def display_data(self):
        self.graph.display_data()
