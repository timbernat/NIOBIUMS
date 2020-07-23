import tkinter as tk
from tkinter import messagebox

import csv, math, os, re 
from collections import Counter
from shutil import rmtree


class Dyn_OptionMenu:
    '''My addon to the TKinter OptionMenu, adds methods to conveniently update menu contents'''
    def __init__(self, frame, var, option_method, default=None, width=10, row=0, col=0, colspan=1):
        self.option_method = option_method
        self.default=default
        self.menu = tk.OptionMenu(frame, var, (None,) )
        self.menu.configure(width=width)
        self.menu.grid(row=row, column=col, columnspan=colspan)
        
        self.var = var
        self.contents = self.menu.children['menu']
        self.update()
    
    def set_default(self):
        self.var.set(self.default)
    
    def update(self):
        self.contents.delete(0, 'end')
        for option in self.option_method():
            self.contents.add_command(label=option, command=lambda x=option: self.var.set(x))
        self.set_default()


class LabelledEntry:
    '''An entry with an adjacent label to the right. Use "self.get_value()" method to retrieve state of
    variable. Be sure to leave two columns worth of space for this widget'''
    def __init__(self, frame, text, var, state='normal', default=None, width=10, row=0, col=0):
        self.default = default
        self.var = var
        self.reset_default()
        self.label = tk.Label(frame, text=text, state=state)
        self.label.grid(row=row, column=col)
        self.entry = tk.Entry(frame, width=width, textvariable=self.var, state=state)
        self.entry.grid(row=row, column=col+1)
        
    def get_value(self):
        return self.var.get()
    
    def set_value(self, value):
        self.var.set(value)
    
    def reset_default(self):
        self.var.set(self.default)
    
    def configure(self, **kwargs):   # allows for disabling in ToggleFrames
        self.label.configure(**kwargs)
        self.entry.configure(**kwargs)


class ToggleFrame(tk.LabelFrame):
    '''A frame whose contents can be easily disabled or enabled, If starting disabled, must put "self.disable()"
    AFTER all widgets have been added to the frame'''
    def __init__(self, window, text, default_state='normal', padx=5, pady=5, row=0, col=0):
        tk.LabelFrame.__init__(self, window, text=text, padx=padx, pady=pady, bd=2, relief='groove')
        self.grid(row=row, column=col)
        self.state = default_state
        self.apply_state()
    
    def apply_state(self):
        for widget in self.winfo_children():
            widget.configure(state = self.state)
            
    def enable(self):
        self.state = 'normal'
        self.apply_state()
     
    def disable(self):
        self.state ='disabled'
        self.apply_state()
    
    def toggle(self):
        if self.state == 'normal':
            self.disable()
        else:
            self.enable()


class StatusBox:
    '''A simple label which changes color and gives indictation of the status of something'''
    def __init__(self, frame, on_message='On', off_message='Off', status=False, width=17, padx=0, row=0, col=0):
        self.on_message = on_message
        self.off_message = off_message
        self.status_box = tk.Label(frame, width=width, padx=padx)
        self.status_box.grid(row=row, column=col)
        self.set_status(status)
        
    def set_status(self, status):
        if type(status) != bool:
            raise Exception(TypeError)
        
        if status:
            self.status_box.configure(bg='green2', text=self.on_message)
        else:
            self.status_box.configure(bg='light gray', text=self.off_message)

            
class Switch: 
    '''A switch button, clicking inverts the boolean state and button display. State can be accessed via
    the <self>.state() method or with the <self>.var.get() attribute to use dynamically with tkinter'''
    def __init__(self, frame, text, value=False, dep_state='normal', dependents=None, width=10, row=0, col=0):
        self.label = tk.Label(frame, text=text)
        self.label.grid(row=row, column=col)
        self.switch = tk.Button(frame, width=width, command=self.toggle)
        self.switch.grid(row=row, column=col+1)
    
        self.dependents = dependents
        self.dep_state = dep_state
        self.value = value
        self.apply_state()
    
    def get_text(self):
        return self.value and 'Enabled' or 'Disabled'
        
    def get_color(self):
        return self.value and 'green2' or 'red' 
    
    def apply_state(self):
        self.dep_state = (self.value and 'normal' or 'disabled')
        self.switch.configure(text=self.get_text(), bg=self.get_color())
        if self.dependents:
            for widget in self.dependents:
                widget.configure(state=self.dep_state)
                
    def enable(self):
        self.value = True
        self.apply_state()
     
    def disable(self):
        self.value = False
        self.apply_state()
    
    def toggle(self):
        if self.value:
            self.disable()
        else:
            self.enable()  
            
        
class CustomDialog:
    '''A custom dialog box for after splitting'''
    def __init__(self, main, reset_method, exit_method):
        self.dialog = tk.Toplevel(main)
        self.dialog.title('Splitting Complete')
        self.dialog.geometry('305x100')
        
        self.reset_method = reset_method
        self.exit_method = exit_method
        
        #info
        self.text = tk.Label(self.dialog, text='Splitting procedure successful.\n\nResults in application folder',
                             padx=70, pady=12, bd=2, relief='groove')
        self.text.grid(row=0, column=0)
    
        # buttons
        self.button_frame = tk.Frame(self.dialog)
        self.reset_button = tk.Button(self.button_frame, text='Split Another', bg='orange', padx=40, command=self.reset)
        self.exit_button = tk.Button(self.button_frame, text='Exit', bg='red', padx=58, command=self.exit)
        
        self.button_frame.grid(row=1, column=0)
        self.reset_button.grid(row=0, column=0)
        self.exit_button.grid(row=0, column=1)
    
    def reset(self):
        self.dialog.destroy()
        self.reset_method()
        
    def exit(self):
        self.dialog.destroy()
        self.exit_method()


class GroupableCheck():
    '''A checkbutton which will add or remove its value to an output list
    (passed as an argument when creating an instance) based on its check status'''
    def __init__(self, frame, value, output, state='normal', row=0, col=0):
        self.var = tk.StringVar()
        self.value = value
        self.output = output
        self.state = state
        self.cb = tk.Checkbutton(frame, text=value, variable=self.var, onvalue=self.value, offvalue=None,
                              state=self.state, command=self.edit_output)
        self.cb.grid(row=row, column=col, sticky='w')
        self.cb.deselect()
        
    def edit_output(self):
        if self.var.get() == self.value:
            self.output.append(self.value)
        else:
            self.output.remove(self.value)
            
    def configure(self, **kwargs):
        self.cb.configure(**kwargs)
            
class CheckPanel():
    '''A panel of GroupableChecks, allows for simple selectivity of the contents of some list'''
    def __init__(self, frame, data, output, state='normal', ncols=4, row_start=0, col_start=0):
        self.output = output
        self.state = state
        self.row_span = math.ceil(len(data)/ncols)
        self.panel = [ GroupableCheck(frame, val, output, state=self.state, row=row_start + i//ncols,
                                      col=col_start + i%ncols) for i, val in enumerate(data) ]
        
    def wipe_output(self):
        self.output.clear()
        
    def apply_state(self):
        for gc in self.panel:
            gc.configure(state=self.state)
    
    def enable(self):
        self.state = 'normal'
        self.apply_state()
     
    def disable(self):
        self.state = 'disabled'
        self.apply_state()
    
    def toggle(self):
        if self.state == 'normal':
            self.disable()
        else:
            self.enable()        
        
class SelectionWindow():
    '''The window used to select unfamiliars'''
    def __init__(self, main, parent_frame, size, selections, output, ncols=1):
        self.window = tk.Toplevel(main)
        self.window.title('Select Members to Include')
        self.window.geometry(size)
        self.parent = parent_frame
        self.parent.disable()
        
        self.panel = CheckPanel(self.window, selections, output, ncols=ncols)
        self.confirm = tk.Button(self.window, text='Confirm Selection', command=self.confirm, padx=5)
        self.confirm.grid(row=self.panel.row_span, column=ncols-1)

    def confirm(self):
        self.parent.enable()
        self.window.destroy()       


class SPLIT_App:
    '''The Separation App itself. NIOBI-UMS = NeuralWare I/O Bookend Interface for Unlabelled Mobility Spectra'''
    def __init__(self, main):
        self.main = main
        self.main.title('NIOB-IUMS-1.0-alpha')
        self.main.geometry('445x195')

        #Frame 1
        self.data_frame = ToggleFrame(self.main, 'Select CSV to Read: ', padx=21, pady=5, row=0)
        self.chosen_file = tk.StringVar()
        self.chem_data = {}
        self.all_species = set()
        self.families = set()
        self.family_mapping = {}
        self.species_count = Counter()
        self.kept_species_count = Counter()
        
        self.csv_menu = Dyn_OptionMenu(self.data_frame, self.chosen_file, self.get_csvs, default='--Choose a CSV--', width=28, colspan=2)
        self.read_label = tk.Label(self.data_frame, text='Read Status:')
        self.read_status = StatusBox(self.data_frame, on_message='CSV Read!', off_message='No File Read', row=1, col=1)
        self.refresh_button = tk.Button(self.data_frame, text='Refresh CSVs', command=self.csv_menu.update, padx=15)
        self.confirm_button = tk.Button(self.data_frame, text='Confirm Selection', padx=2, command=self.import_data)
        
        self.refresh_button.grid(row=0, column=2)
        self.read_label.grid(row=1, column=0)
        self.confirm_button.grid(row=1, column=2)
        
        
        #Frame 2
        self.species_frame = ToggleFrame(self.main, 'Select a Species to Isolate', padx=32, pady=5, row=1)
        self.unfamiliars = []
        self.select_unfams = tk.BooleanVar()
        self.learn_file_titles = []
        self.test_file_titles = []

        self.split_prop_entry = LabelledEntry(self.species_frame, 'Set Proportion for Learn: ', tk.DoubleVar(), default=0.75)
        self.unfam_check = tk.Checkbutton(self.species_frame, text='Unfamiliars?', variable=self.select_unfams, command=self.further_sel)
        self.splitting_button = tk.Button(self.species_frame, text='Perform Splitting', padx=2, command=self.separate_and_write)
        
        self.unfam_check.grid(row=0, column=2, sticky='w')
        self.splitting_button.grid(row=1, column=2, sticky='w')
        
        
        #Misc/Other
        self.exit_button = tk.Button(self.main, text='Exit', padx=22, pady=23, bg='red', command=self.exit)
        self.reset_button = tk.Button(self.main, text='Reset', padx=16, pady=12, bg='orange', command=self.reset)
        self.plot_button = tk.Button(self.main, text='Plot Results (WIP)', padx=134, bg='dodger blue', command=lambda : None)
        self.exit_button.grid(row=0, column=1)
        self.reset_button.grid(row=1, column=1)
        self.plot_button.grid(row=2, column=0)
        
        self.arrays = (self.chem_data, self.family_mapping, self.unfamiliars, self.species_count, self.kept_species_count, self.learn_file_titles, self.test_file_titles)
        self.frames = (self.data_frame, self.species_frame)
        self.isolate(self.data_frame)
    
    #General Methods
    def isolate(self, on_frame):
        '''Enable just one frame.'''
        for frame in self.frames:
            if frame == on_frame:
                frame.enable()
            else:
                frame.disable()   
    
    def reset(self):
        '''Reset the menu and internal variables to their original state'''   
        for datum in self.arrays:
            datum.clear() 
        self.all_species, self.families = set(), set()
        
        self.read_status.set_status(False)
        self.csv_menu.set_default()
        self.split_prop_entry.reset_default()
        self.unfam_check.deselect()
        
        self.isolate(self.data_frame)
    
    def exit(self):
        '''Close the application, with confirm prompt'''
        if messagebox.askokcancel('Exit', 'Are you sure you want to close?'):
            self.main.destroy()
            
            
    #Frame 1 (File selection) Methods    
    def get_species(self, species):
        '''Strips extra numbers off the end of the name of a' species in a csv and just tells you the species name'''
        return re.sub('(\s|-)\d+\s*\Z', '', species)  # regex to crop off terminal digits in a variety of possible 
            
    def get_family(self, species):
        '''Takes the name of a species and returns the chemical family that that species belongs to, based on IUPAC naming conventions'''
        iupac_suffices = {  'ate':'Acetates',
                            'ol':'Alcohols',
                            'al':'Aldehydes',
                            'ane':'Alkanes',
                            'ene':'Alkenes',
                            'yne':'Alkynes',
                            'ine':'Amines',
                            'oic acid': 'Carboxylic Acids',
                            #'ate':'Esters',
                            'ether':'Ethers',
                            'one':'Ketones'  }                    
        for regex, family in iupac_suffices.items():
            # ratioanle for regex: ignore capitalization (particular to ethers), only check end of name (particular to pinac<ol>one)
            if re.search('(?i){}\Z'.format(regex), self.get_species(species) ):  
                return family
    
    def read_chem_data(self): 
        '''Used to read and format the data from the csv provided into a form usable by the training program
        Returns the read data (with vector) and sorted lists of the species and families found in the data'''
        csv_name = './{}.csv'.format( self.chosen_file.get() )
        with open(csv_name, 'r') as file:
            for line in csv.reader(file):
                instance, spectrum, curr_species = line[0], line[1:], self.get_species(line[0])
                
                self.chem_data[instance] = spectrum
                self.all_species.add(curr_species)
                self.species_count[curr_species] += 1
                self.families.add( self.get_family(instance) )
        self.all_species, self.families = sorted(self.all_species), sorted(self.families)  # sort and convert to lists
        
        for family in self.families:
            one_hot_vector = [i == family and '1' or '0' for i in self.families]  # bits must be str, not int, for writing reasons
            self.family_mapping[family] = one_hot_vector
                                   
        for instance in self.chem_data.keys():  # add mapping vector to all data entries
            vector = self.family_mapping[ self.get_family(instance) ]
            for bit in vector:
                self.chem_data[instance].append(bit)
    
    def get_csvs(self):
        '''Update the CSV dropdown selection to catch any changes in the files present'''
        csvs_present = tuple(i[:-4] for i in os.listdir('.') if re.search('.csv\Z', i))
        if csvs_present == ():
            csvs_present = (None,)
        return csvs_present
    
    def import_data(self):
        '''Read in data based on the selected data file'''
        if self.chosen_file.get() == '--Choose a CSV--':
            messagebox.showerror('File Error', 'No CSV selected')
        else:
            self.read_chem_data()
            self.read_status.set_status(True)
            self.isolate(self.species_frame)
    
    
    #Frame 2 (species selection and separation) methods
    def further_sel(self): 
        '''logic for selection of members to include in training'''
        self.unfamiliars.clear()
        if self.select_unfams.get():
            SelectionWindow(self.main, self.species_frame, '960x190', self.all_species, self.unfamiliars, ncols=8)
    
    def separate_and_write(self):
        split_proportion = self.split_prop_entry.get_value()
        
        result_str = '{}-{} split'.format(split_proportion, 1 - split_proportion)
        for species, count in self.species_count.items():
            self.kept_species_count[species] = round(split_proportion*count)   # a separate counter which tells how many of each species should be kept (ignoring any unfamiliars)
        
        if self.unfamiliars:
            result_str = '{}, No {}'.format(result_str, ', '.join(self.unfamiliars))  # if unfamiliars are being selected for, add them to the result name and ensure none will be kept
            for unfamiliar in self.unfamiliars:
                self.kept_species_count[unfamiliar] = 0
        
        file_dir = 'Training Files, ' + result_str
        if file_dir not in os.listdir('.'):  # check for existing file, overwrite identical file with user permission
            os.mkdir(file_dir)
        elif messagebox.askyesno('Duplicates Found', 'Folder with same data settings found\nOverwrite old folder?'):
            rmtree(file_dir, ignore_errors=True)
            os.mkdir(file_dir)
        else:
            return

        test_path, learn_path = '{}/TTT_{}.txt'.format(file_dir, result_str), '{}/LLL_{}.txt'.format(file_dir, result_str)   
        with open(test_path, 'w') as test_file, open(learn_path, 'w') as learn_file:
            for instance, data in self.chem_data.items():
                formatted_entry = '{}\n'.format(instance + '\t'.join(data))
                curr_species = self.get_species(instance)
                
                if self.species_count[curr_species] > self.kept_species_count[curr_species]:
                    self.test_file_titles.append(instance)
                    test_file.write(formatted_entry)
                    self.species_count[curr_species] -= 1
                else:
                    self.learn_file_titles.append(instance)
                    learn_file.write(formatted_entry)   
        CustomDialog(self.main, self.reset, self.exit)
        
if __name__ == '__main__':        
    main_window = tk.Tk()
    app = SPLIT_App(main_window)
    main_window.mainloop()
