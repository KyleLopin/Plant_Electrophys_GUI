import tkinter as tk
import os
import shelve
import logging
import csv
import datetime

__author__ = 'Kyle Vitautas Lopin'


class SaveTopLevel(tk.Toplevel):
    def __init__(self, _master, x_data=[1], y_data=[1]):
        tk.Toplevel.__init__(self, master=_master)
        self.geometry('400x300')
        self.title("Save data")
        self.master = _master
        self.x = x_data
        self.y = y_data
        self.data_was_saved = False

        # make file name string
        date = str(datetime.date.today())
        date_str = date[2:4]+date[5:7]+date[8:]
        num_str = str(_master.save_state.file_number).zfill(3)
        self.filename_str = self.master.save_state.branch + date_str + '_' + num_str

        # make frame to make a generic name to suggest to the user
        filename_frame = tk.Frame(self)
        filename_frame.pack(side='top')
        tk.Label(filename_frame, text="File name to save as: ").pack(side='left')
        self._filename_var = tk.StringVar()
        self._filename_var.trace("w", self.update_filename)
        self.filename_entry = tk.Entry(filename_frame, textvariable=self._filename_var)
        # filename_entry.delete(0, "end")
        # filename_entry.insert(0, self.filename_str)
        fill_in_filename(self.filename_entry, self.filename_str)
        self.filename_entry.pack(side='left')
        # make spinbox to label wich branch
        branch_frame = tk.Frame(self)
        branch_frame.pack(side='top')
        tk.Label(branch_frame, text="Branch letter: ").pack(side='left')
        _branch_var = tk.StringVar()
        _branch_var.set(self.master.save_state.branch)
        branch_spinbox = tk.Spinbox(branch_frame, width=6,
                                    values=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
                                    command=lambda: self.branch_change(branch_spinbox.get()))
        branch_spinbox.delete(0, "end")
        branch_spinbox.insert(0, self.master.save_state.branch)
        branch_spinbox.pack(side='left')

        # make save and cancel buttons
        button_frame = tk.Frame(self)
        button_frame.pack(side='bottom')
        tk.Button(button_frame, text="Save File", command=self.save).pack(side='left', padx=20)
        tk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='left', padx=20)

    def destroy(self):
        return self.data_was_saved

    def save(self):
        try:  # if the user changed the last number of the file name try to update the next filename
            new_number = int(self.filename_str[-3:])
            self.master.save_state.file_number = new_number
        except:
            pass

        path = os.getcwd()
        data_path = path+'/data/'+self.filename_str[1:7]
        # check if user is attempting to overwrite a data file
        valid_file_name = False
        while not valid_file_name:
            if os.path.isfile(data_path+'/'+self.filename_str+'.csv'):
                new_file_num = int(self.filename_str[-3:]) + 1
                self.filename_str = self.filename_str[:-3]+str(new_file_num).zfill(3)
                self.master.save_state.file_number = new_file_num
            else:
                valid_file_name = True

        else:  # make csv file
            with open(data_path+'/'+self.filename_str+'.shlv', 'wb') as csvfile:
                writer = csv.writer(csvfile, dialect='excel')
                writer.writerow(['time', 'voltage'])
                for i, x_pt in enumerate(self.x):
                    _row = [x_pt]
                    for y_pt in self.y:  # y is a list of lists of points
                        _row.append(y_pt[i])
                    writer.writerow(_row)
        print('done')
        self.master.save_state.file_number += 1
        logging.info("Saved data in %s" % self.filename_str)
        self.data_was_saved = True
        self.destroy()

    def update_filename(self, *args):
        self.filename_str = self._filename_var.get()

    def branch_change(self, value):
        self.master.save_state.branch = value
        self.filename_str = value + self.filename_str[1:]
        fill_in_filename(self.filename_entry, self.filename_str)


def fill_in_filename(_entry, filename):
    _entry.delete(0, "end")
    _entry.insert(0, filename)


class SaveState(object):
    def __init__(self, old_date):
        # check for a save state file first
        try:
            state_data = shelve.open('state.db')
            if state_data['date'] == old_date:
                self.branch = state_data['branch']
                self.file_number = state_data['file number']
                return
        except:
            pass
        self.branch = 'A'
        self.file_number = 1



if __name__ == '__main__':
    app = tk.Tk()
    app.save_state = SaveState()
    app.save_state.branch = 'C'
    x = [1, 2, 3, 4]
    y = [[2, 2, 2, 4], [4, 5, 6, 7]]
    SaveTopLevel(app, x, y)
    app.mainloop()