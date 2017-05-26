import tkinter as tk
import tkinter.constants
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib import pyplot as plt
import matplotlib.animation as animation

__author__ = 'Kyle Vitautas Lopin'

sample_rate = 10000  # Hz
sample_period = 1. / sample_rate  # seconds

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
        self.draw_new_data([0], [[0]], 5)
        self.canvas.draw()

    def set_time_frame(self, time):
        self.time_to_display = time

    def draw_new_data(self, x, y_array, time_display):

        # print('drawing data: ', x[0:10], x[-1], time_display)
        # self.axis.clear()
        for i, y in enumerate(y_array):
            _line, = self.axis.plot(x, y, label='channel %d' % (i+1))
            self.lines.append(_line)
        self.axis.set_xlim([x[-1]-time_display, x[-1]])
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
        self.axis.set_xlim([t_end - self.time_to_display, t_end])
        # self.axis.legend(loc=1)
        self.axis.relim()
        self.axis.autoscale_view(True, True, True)
        self.canvas.draw()

