
import tkinter as tk

# local files
import usb_comm

__author__ = 'Kyle Vitautas Lopin'

MAX_CURRENT = 255
MIN_CURRENT = 1



class Stimulator(tk.Toplevel):
    def __init__(self, device: usb_comm.PlantUSB, parent=None):
        tk.Toplevel.__init__(self, parent)
        self.device = device
        self.geometry("500x450")
        self.title("Stimulator")
        self.prepared = False
        self.run_button = None  # placeholder so trace callback doesn't throw an error
        self.current = tk.IntVar()
        self.current.trace("w", self.variable_changed)
        self.time = tk.IntVar()
        self.time.trace("w", self.variable_changed)
        self.channel = tk.IntVar()
        self.channel.trace("w", self.variable_changed)
        self.polarity = tk.StringVar()
        self.polarity.trace("w", self.variable_changed)

        tk.Label(self, text="Current level to give").grid(row=0,column=0)

        tk.Spinbox(self, from_=1, to=255, textvariable=self.current,
                   command=self.variable_changed).grid(row=0,column=1)
        tk.Label(self, text="microamperes").grid(row=0,column=2)

        tk.Label(self, text="Time to give").grid(row=1, column=0)

        tk.Spinbox(self, from_=1, to=60000, increment=100,
                   textvariable=self.time, command=self.variable_changed).grid(row=1, column=1)

        tk.Label(self, text="milliseconds").grid(row=1, column=2)

        tk.Label(self, text="Stimulation channel: ").grid(row=2, column=0)

        tk.Spinbox(self, from_=1, to=3, textvariable=self.channel,
                   command=self.variable_changed).grid(row=2, column=1)

        # tk.Label(self, text='Current direction:').grid(row=3, column=0)
        # tk.Radiobutton(self, text='Source',
        #                variable=self.polarity, value='Source').grid(row=3, column=1)
        # tk.Radiobutton(self, text='Sink',
        #                variable=self.polarity, value='Sink',
        #                command=self.variable_changed).grid(row=3, column=2)

        self.run_button = tk.Button(self, text="Prepare Stimulator", command=self.prepare)
        self.run_button.grid(row=10, column=1)

        self.time.set(1000)
        self.polarity.set('Source')

    def variable_changed(self, *args):
        if self.run_button:
            self.prepared = False
            self.run_button.config(text="Prepare Stimulator", command=self.prepare)

    def prepare(self):
        self.device.set_stimulator(self.time.get(), self.current.get(), self.channel.get(), self.polarity.get())
        # fix the variables in case the user put some crap in there
        for i in [self.current, self.time, self.channel]:
            update_entries(i)
        self.run_button.config(text="Stimulate", command=self.stimulate)
        self.prepared = True

    def stimulate(self):
        self.device.give_stimulation()


def update_entries(entry):
    entry.set(entry.get())


if __name__ == '__main__':
    app = Stimulator('1')
    app.mainloop()
