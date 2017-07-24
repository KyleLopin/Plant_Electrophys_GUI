import tkinter as tk
import tkinter.constants
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib import pyplot as plt
import matplotlib.animation as animation

__author__ = 'Kyle Vitautas Lopin'

sample_rate = 5000  # Hz
sample_period = 1. / sample_rate  # seconds

COLORS = ['black', 'blue', 'red', 'green']

class Plotter(tk.Frame):
    def __init__(self, parent, data, _size=(6, 3)):
        tk.Frame.__init__(self, master=parent)
        self.data = data
        self.time_to_display = 5
        self.lines = []
        self.base_canvas = tk.Canvas(self)

        self.figure_bed = plt.figure(figsize=_size)
        self.axis = self.figure_bed.add_subplot(111)

        # self.figure_bed.set_facecolor('white')
        self.canvas = FigureCanvasTkAgg(self.figure_bed, self)
        self.canvas._tkcanvas.config(highlightthickness=0)

        toolbar = NavigationToolbar2TkAgg(self.canvas, self)
        toolbar.update()

        self.canvas._tkcanvas.pack(side='top', fill=tk.BOTH, expand=True)
        self.draw_new_data([0], [[0]], self.time_to_display)
        self.canvas.draw()

    def set_time_frame(self, time):
        self.time_to_display = time

    def draw_new_data(self, x, y_array, time_display=None):

        # print('drawing data: ', x[0:10], x[-1], time_display)
        # self.axis.clear()
        while self.lines:
            old_line = self.lines.pop()
            old_line.remove()
            del old_line
        if not time_display:
            time_display = self.time_to_display
        for i, y in enumerate(y_array):
            _line, = self.axis.plot(x, y, label='channel %d' % (i+1), c=COLORS[i])
            self.lines.append(_line)
        self.axis.set_xlim([self.data.end_time-time_display, self.data.end_time])  # hackish
        self.axis.legend(loc=1)
        self.canvas.draw()

    def display_data(self):
        # self.axis.clear()
        y_data = self.data.y_data_to_display
        x = self.data.t_data
        t_end = self.data.end_time
        for i, y in enumerate(y_data):
            # self.axis.plot(x, y, label='channel %d' % (i+1))
            self.lines[i].set_data(x, y)
            # print('y data: ', y[:500])
        self.axis.set_xlim([t_end - self.time_to_display, t_end])
        # self.axis.legend(loc=1)
        self.axis.relim()
        self.axis.autoscale_view(True, True, True)
        self.canvas.draw()

    def set_num_channels(self, num_channels):
        diff_channels = len(self.lines) - num_channels
        if diff_channels < 0:  # there are more lines currently displayed than the user chose
            pass
