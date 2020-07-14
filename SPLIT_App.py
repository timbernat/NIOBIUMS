import tkinter as tk
from tkinter import messagebox

import csv, math, os, re 
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
    '''The Separation App itself'''
    def __init__(self, main):
        self.main = main
        self.main.title('SPLIT-1.1')
        self.main.geometry('445x145')

        #Frame 1
        self.data_frame = ToggleFrame(self.main, 'Select CSV to Read: ', padx=21, pady=5, row=0)
        self.chosen_file = tk.StringVar()
        self.data_from_file = {}
        self.all_species = set()
        self.families = set()
        self.family_mapping = {}
        
        self.csv_menu = Dyn_OptionMenu(self.data_frame, self.chosen_file, self.get_csvs, default='--Choose a CSV--', width=28, colspan=2)
        self.read_label = tk.Label(self.data_frame, text='Read Status:')
        self.read_status = tk.Label(self.data_frame, bg='light gray', padx=30, text='No File Read')
        self.refresh_button = tk.Button(self.data_frame, text='Refresh CSVs', command=self.csv_menu.update, padx=15)
        self.confirm_button = tk.Button(self.data_frame, text='Confirm Selection', padx=2, command=self.import_data)
        
        self.refresh_button.grid(row=0, column=2)
        self.read_label.grid(row=1, column=0)
        self.read_status.grid(row=1, column=1)
        self.confirm_button.grid(row=1, column=2)
        
        
        #Frame 2
        self.species_frame = ToggleFrame(self.main, 'Select a Species to Isolate', padx=21, pady=5, row=1)
        self.read_mode = tk.StringVar()
        self.read_mode.set(None)
        self.selections = []
        
        self.mode_buttons = []
        for i, mode in enumerate( ('By Family', 'By Species') ):
            self.mode_buttons.append( tk.Radiobutton(self.species_frame, text=mode, value=mode, padx=15, 
                                                     var=self.read_mode, command=self.further_sel) )
            self.mode_buttons[i].grid(row=0, column=i)
        self.splitting_button = tk.Button(self.species_frame, text='Perform Splitting', padx=2, command=self.separate_and_write)
        self.splitting_button.grid(row=0, column=3)
        
        
        #Misc/Other
        self.exit_button = tk.Button(self.main, text='Exit', padx=22, pady=23, bg='red', command=self.exit)
        self.reset_button = tk.Button(self.main, text='Reset', padx=16, pady=12, bg='orange', command=self.reset)
        self.exit_button.grid(row=0, column=1)
        self.reset_button.grid(row=1, column=1)
        
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
        self.read_status.configure(bg='light gray', text='No File Read')
        self.csv_menu.set_default()
            
        for datum in (self.data_from_file, self.family_mapping, self.selections):
            datum.clear()
            
        self.all_species = set()
        self.families = set()
        self.read_mode.set(None)
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
                            'oic acid': 'Carboxylic Acids',
                            #'ate':'Esters',
                            'ether':'Ethers',
                            'one':'Ketones'  }                    
        for regex, family in iupac_suffices.items():
            if re.search('(?i){}'.format(regex), species):  # ignore case/capitalization (particular to case of ethers)
                return family
    
    def read_chem_data(self): 
        '''Used to read and format the data from the csv provided into a form usable by the training program
        Returns the read data (with vector) and sorted lists of the species and families found in the data'''
        csv_name = './{}.csv'.format( self.chosen_file.get() )
        with open(csv_name, 'r') as file:
            for row in csv.reader(file):
                label, data = row[0], row[1:]
                self.data_from_file[label] = data
                self.all_species.add( self.get_species(label) )
                self.families.add( self.get_family(label) )
        self.all_species, self.families = sorted(self.all_species), sorted(self.families)  # sort and convert to lists
        
        for family in self.families:
            one_hot_vector = [i == family and '1' or '0' for i in self.families]  # bits must be str, not int, for writing reasons
            self.family_mapping[family] = one_hot_vector
                                   
        for species in self.data_from_file.keys():  # add mapping vector to all data entries
            vector = self.family_mapping[ self.get_family(species) ]
            for bit in vector:
                self.data_from_file[species].append(bit)
    
    def get_csvs(self):
        '''Update the CSV dropdown selection to catch any changes in the files present'''
        csvs_present = tuple(i[:-4] for i in os.listdir('.') if re.search('.csv\Z', i))
        if csvs_present == ():
            csvs_present = (None,)
        return csvs_present
    
    def get_all_species(self):
        return(self.all_species)
    
    def import_data(self):
        '''Read in data based on the selected data file'''
        if self.chosen_file.get() == '--Choose a CSV--':
            messagebox.showerror('File Error', 'No CSV selected')
        else:
            self.read_chem_data()
            self.read_status.configure(bg='green2', text='CSV Read!')
            self.isolate(self.species_frame)

    def further_sel(self): 
        '''logic for selection of members to include in training'''
        self.selections.clear()
        if self.read_mode.get() == 'By Species':
            SelectionWindow(self.main, self.species_frame, '960x190', self.all_species, self.selections, ncols=8)
        elif self.read_mode.get() == 'By Family':
            SelectionWindow(self.main, self.species_frame, '265x85', self.families, self.selections, ncols=3)

    
    #Frame 2 (species selection and separation) methods
    def separate_and_write(self):
        if not self.selections:
            messagebox.showerror('No selections made', 'Please select unfamiliars')
            self.read_mode.set(None)
        else:           
            result_str = 'No_{}'.format( ', '.join(self.selections) ) 
            train_file, learn_file = './{}/{}_TTT.txt'.format(result_str, result_str), './{}/{}_LLL.txt'.format(result_str, result_str)
            if self.read_mode.get() == 'By Family':
                self.selections = [species for family in self.selections for species in self.all_species if self.get_family(species) == family]   

            result_dir = './' + result_str  # remove file if one already exists
            if result_str in os.listdir('.'): 
                rmtree(result_dir, ignore_errors=True)
            os.mkdir(result_dir)

            with open(train_file, 'w') as desired, open(learn_file, 'w') as other:
                for species, data in self.data_from_file.items():
                    formatted_entry = '\t'.join(data) + '\n'
                    if self.get_species(species) in self.selections:
                        desired.write(formatted_entry)
                    else:
                        other.write(formatted_entry)      
            CustomDialog(self.main, self.reset, self.exit)
        
if __name__ == '__main__':        
    main_window = tk.Tk()
    app = SPLIT_App(main_window)
    main_window.mainloop()
