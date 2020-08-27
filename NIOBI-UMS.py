import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Progressbar

import iumsutils
import TimTkLib as ttl       # my own tkinter widget library, makes GUI assembly a lot more straightforward

import csv, json, math, os, re   # consider replacing "os" utilities with "pathlib" equivalents
import matplotlib.pyplot as plt

from collections import Counter
from pathlib import Path
from shutil import rmtree     


class PlottingWindow:
    '''A window which displays plotting progress, was easier to subclass outside of the main GUI class'''
    def __init__(self, main, num_cycles):
        self.main = main
        self.training_window = tk.Toplevel(main)
        self.training_window.title('Plotting Progress')
        self.training_window.geometry('373x58')
        
        self.curr_cycle = 0  
        self.num_cycles = num_cycles
        
        # Status Printouts
        self.status_frame = ttl.ToggleFrame(self.training_window, '', padx=13)
        
        self.species_label = tk.Label(self.status_frame, text='Currently Plotting: ')
        self.curr_species = tk.Label(self.status_frame)
        self.progress_label = tk.Label(self.status_frame)
        self.progress = Progressbar(self.status_frame, orient='horizontal', length=240, maximum=self.num_cycles) 
        
        self.species_label.grid(  row=0, column=0)
        self.curr_species.grid(   row=0, column=1, sticky='w')
        self.progress_label.grid( row=1, column=0)
        self.progress.grid(       row=1, column=1, sticky='w')
        
        self.reset()
        
    def reset(self):
        self.set_species('---')
        self.curr_cycle = 0
        self.set_progress(0)
    
    def set_species(self, species):
        self.curr_species.configure(text=species)
        self.main.update()
        
    def set_next_species(self, species):  
        '''For straightforwardly incrementing progress with each new species'''
        self.set_species(species)
        self.curr_cycle += 1
        self.set_progress(self.curr_cycle)
        
    def set_progress(self, cycle):
        self.progress_label.configure(text='Plot: {}/{}'.format(cycle, self.num_cycles) )
        self.progress.configure(value=cycle)
        self.main.update()
        
    def destroy(self):
        self.training_window.destroy()

        
class NIOBIUMS_App:
    '''The Separation App itself. NIOBI-UMS = NeuralWare I/O Bookend Interface for Unlabelled Mobility Spectra'''
    def __init__(self, main):
        self.main = main
        self.main.title('NIOBI-UMS-1.1-alpha')
        self.main.geometry('445x230')

        #Frame 1
        self.data_frame = ttl.ToggleFrame(self.main, 'Select CSV to Read: ', padx=22, pady=5, row=0)
        self.chosen_file = tk.StringVar()
        self.chem_data = {}
        self.all_species = set()
        self.families = set()
        self.family_mapping = {}
        self.species_count = Counter()
        self.kept_species_count = Counter()
        
        self.csv_menu = ttl.DynOptionMenu(self.data_frame, self.chosen_file, iumsutils.get_csvs, default='--Choose a CSV--', width=28, colspan=2)
        self.read_label = tk.Label(self.data_frame, text='Read Status:')
        self.read_status = ttl.StatusBox(self.data_frame, on_message='CSV Read!', off_message='No File Read', row=1, col=1)
        self.refresh_button = tk.Button(self.data_frame, text='Refresh CSVs', command=self.csv_menu.update, padx=15)
        self.confirm_button = ttl.ConfirmButton(self.data_frame, self.import_data, padx=2, row=1, col=2)
        
        self.refresh_button.grid(row=0, column=2)
        self.read_label.grid(row=1, column=0)
        
        
        #Frame 2
        self.species_frame = ttl.ToggleFrame(self.main, 'Set Learn/Test File Parameters:', padx=30, pady=5, row=1)
        self.unfamiliars = []
        self.select_unfams = tk.BooleanVar()
        self.file_dir = None

        self.split_prop_entry = ttl.LabelledEntry(self.species_frame, 'Set Proportion for Learn: ', tk.DoubleVar(), default=0.8)
        self.unfam_check = tk.Checkbutton(self.species_frame, text='Unfamiliars?', variable=self.select_unfams, command=self.further_sel)
        self.splitting_button = tk.Button(self.species_frame, text='Perform Splitting', padx=2, command=self.separate_and_write)
        
        self.unfam_check.grid(row=0, column=2, sticky='w')
        self.splitting_button.grid(row=1, column=2, sticky='w')
        
        
        #Frame 3
        self.plotting_frame = ttl.ToggleFrame(self.main, 'Generate Plots from Training Results', padx=13, row=2)
        self.chosen_train_folder = tk.StringVar()
        self.result_data = {}
        
        self.train_folder_menu = ttl.DynOptionMenu(self.plotting_frame, self.chosen_train_folder, self.get_train_folders, default='--Choose a Training Folder--', width=28, colspan=2)
        self.plot_button = tk.Button(self.plotting_frame, text='Plot Training Results', padx=5, bg='dodger blue', command=self.plot_nnr)
        
        self.plot_button.grid(row=0, column=2)
        
        
        #Misc/Other
        self.exit_button = tk.Button(self.main, text='Exit', padx=22, pady=27, bg='red', command=self.exit)
        self.reset_button = tk.Button(self.main, text='Reset', padx=16, pady=14, bg='orange', command=self.reset)
        self.exit_button.grid(row=0, column=1, sticky='s')
        self.reset_button.grid(row=2, column=1, sticky='s')
        
        self.arrays = (self.chem_data, self.family_mapping, self.unfamiliars, self.species_count, self.kept_species_count, self.result_data)
        self.frames = (self.data_frame, self.species_frame, self.plotting_frame)
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
        self.file_dir = None
        
        self.read_status.set_status(False)
        self.csv_menu.reset_default()
        self.split_prop_entry.reset_default()
        self.unfam_check.deselect()
        
        self.isolate(self.data_frame)
    
    def get_train_folders(self):  # NOTE: consider converting this to a regex-dependent expression based on DynOptionMenu in TimTkLib
        '''Return a list of all training files folders present in the current directory'''
        tfs_present = tuple(i for i in os.listdir() if re.search('\ATraining Files', i))
        if tfs_present == ():
            tfs_present = (None,)
        return tfs_present
    
    def exit(self):
        '''Close the application, with confirm prompt'''
        if messagebox.askokcancel('Exit', 'Are you sure you want to close?'):
            self.main.destroy()
            
            
    #Frame 1 (File selection) Methods     
    def read_chem_data(self): 
        '''Used to read and format the data from the csv provided into a form usable by the training program
        Returns the read data (with vector) and sorted lists of the species and families found in the data'''
        with open(self.chosen_file.get(), 'r') as file:
            for row in csv.reader(file):
                instance, curr_species, spectrum = row[0], iumsutils.isolate_species(row[0]), [float(i) for i in row[1:]]
                
                self.chem_data[instance] = spectrum
                self.all_species.add(curr_species)
                self.species_count[curr_species] += 1
                self.families.add(iumsutils.get_family(instance))
        self.all_species, self.families = sorted(self.all_species), sorted(self.families)  # sort and convert to lists
        
        for family in self.families:
            one_hot_vector = [int(i == family) for i in self.families]  # bits must be str, not int, for writing reasons
            self.family_mapping[family] = one_hot_vector
                                   
        for instance, data in self.chem_data.items():  # add mapping vector to all data entries
            vector = self.family_mapping[iumsutils.get_family(instance)]
            self.chem_data[instance] = (data, vector)
    
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
        '''logic for selection of speciess to include in training'''
        self.unfamiliars.clear()
        if self.select_unfams.get():
            ttl.SelectionWindow(self.main, self.species_frame, '960x190', self.all_species, self.unfamiliars, ncols=8)
    
    def adagraph(self, plot_list, ncols, save_dir):  # ADD AXIS LABELS!
        '''a general tidy internal graphing utility of my own devising, used to produce all manner of plots during training with one function'''
        nrows = math.ceil(len(plot_list)/ncols)  #  determine the necessary number of rows needed to accomodate the data
        display_size = 20                        # 20 seems to be good size for jupyter viewing
        fig, axs = plt.subplots(nrows, ncols, figsize=(display_size, display_size * nrows/ncols)) 
        
        for idx, (plot_data, plot_title, plot_type) in enumerate(plot_list):                         
            if nrows > 1:                        # locate the current plot, unpack linear index into coordinate
                row, col = divmod(idx, ncols)      
                curr_plot = axs[row][col]  
            else:                                # special case for indexing plots with only one row; my workaround of implementation in matplotlib
                curr_plot = axs[idx]    
            curr_plot.set_title(plot_title)

            if plot_type == 'f':               # for plotting fermi-dirac plots
                curr_plot.plot(plot_data, 'm-')  
                curr_plot.set_ylim(0, 1.05)
            elif plot_type == 'p':               # for plotting predictions
                curr_plot.bar( self.family_mapping.keys(), plot_data, color=('Summation' in plot_title and 'r' or 'b'))  
                curr_plot.set_ylim(0,1)
                curr_plot.tick_params(axis='x', labelrotation=45)
        plt.tight_layout()
        plt.savefig(save_dir)
        plt.close('all')
    
    
    def separate_and_write(self):
        split_proportion = self.split_prop_entry.get_value()
        split_complement = round(1 - split_proportion, 4)   # rounding to 4 places should avoid float error for typical proportions (noted here for future debugging)
        
        for species, count in self.species_count.items():
            if species in self.unfamiliars:
                self.kept_species_count[species] = 0  # do not keep any unfamiliars
            else:
                self.kept_species_count[species] = round(split_proportion*count)  # if not an unfamiliar, set the amount to keep based on the set proportion

        if self.select_unfams.get():   # if unfamiliars have been chosen
            training_desc = 'No {}'.format(', '.join(self.unfamiliars))  
        else:
            training_desc = 'Control Run'
        self.file_dir = Path('Training Files', '{}-{} split, {}'.format(split_proportion, split_complement, training_desc))

        if os.path.exists(self.file_dir):   # prompt user to overwrite file if one already exists
            if messagebox.askyesno('Duplicates Found', 'Folder with same data settings found;\nOverwrite old folder?'):
                rmtree(self.file_dir, ignore_errors=True)
            else:
                return  #terminate prematurely if overwrite permission is not given
        os.makedirs(self.file_dir)
        
        learn_labels, test_labels = [], []
        with open(Path(self.file_dir, 'TTT_testfile.txt'), 'w') as test_file, open(Path(self.file_dir, 'LLL_learnfile.txt'), 'w') as learn_file:    
            for instance, (spectrum, vector) in self.chem_data.items():   # separate read csv data into learn and test files on the basis of the species Counters
                stringy_data = [str(i) for i in spectrum] + [str(i) for i in vector] # convert numerical data to str for writing, expand tailing vector
                formatted_entry = '\t'.join(stringy_data) + '\n'    # data is tab-separated and followed by a newline character for separation
                curr_species = iumsutils.isolate_species(instance)
                
                if self.species_count[curr_species] > self.kept_species_count[curr_species]:  # if the current amount of a species present is greater than the amount we'd like to keep
                    test_labels.append(instance)
                    test_file.write(formatted_entry)
                    self.species_count[curr_species] -= 1
                else:
                    learn_labels.append(instance)
                    learn_file.write(formatted_entry) 
                               
        with open(Path(self.file_dir, 'Test Labels.json'), 'w') as test_labels_file, open(Path(self.file_dir, 'Learn Labels.json'), 'w') as learn_labels_file: 
            json.dump(test_labels, test_labels_file)    # write the labels associated with each file to jsons for records and later access if replotting
            json.dump(learn_labels, learn_labels_file)
        messagebox.showinfo('File Creation Successful!', 'Files can be found in "Training Files" folder\n\nPlease perform training, then proceed to plotting')
        
        self.isolate(self.plotting_frame)
        self.train_folder_menu.update()
        #self.train_folder_menu.var.set(self.file_dir)  # make the selection the current folder, sidestep selection
        self.train_folder_menu.disable()
        
        
    def plot_nnr(self):
        if 'TTT_testfile_txt.nnr' not in os.listdir(self.file_dir):
            messagebox.showerror('No NNR File Present!', 'Please perform training before attempting plotting')
        else:
            with open(Path(self.file_dir, 'Test Labels.json'), 'r') as test_labels_file:
                test_labels = json.load(test_labels_file)
            
            num_plots = 1 # start count at 1 to account for the extra Fermi Plot summary
            with open(Path(self.file_dir, 'TTT_testfile_txt.nnr'), 'r') as result_file:
                for idx, row in enumerate(result_file):
                    instance, curr_species, curr_family = test_labels[idx], iumsutils.isolate_species(test_labels[idx]), iumsutils.get_family(test_labels[idx])
                                
                    row_data = tuple( float(i) for i in re.split('\t|\n', row)[1:-1] )  # remove tab and newline chars, cut off empty strings at start and end, and convert to floats
                    vector, aavs = row_data[:5], row_data[5:], 
                    target = aavs[vector.index(1)]
   
                    if curr_family not in self.result_data:   # ensuring no key errors occur due to missing entry key 
                        self.result_data[curr_family] = {}
                    if curr_species not in self.result_data[curr_family]:
                        self.result_data[curr_family][curr_species] = ( [], [], [], Counter() )
                        num_plots += 1  # each new species will produce 1 extra plot
                    names, predictions, fermi_data, corr_count = self.result_data[curr_family][curr_species]
                    
                    names.append(instance)
                    predictions.append(aavs)
                    fermi_data.append(target)
                    corr_count['total'] += 1
                    if target == max(aavs):
                        corr_count['correct'] += 1
                
            plot_window = PlottingWindow(self.main, num_plots)    
            os.mkdir(Path(self.file_dir, 'Result Plots'))  # expand this simlar to other file control in order to be a bit more discerning with pre-existing files
            with open(Path(self.file_dir, 'Result Plots', 'Scores.txt'), 'w') as score_file:       
                fermi_summary = []
                
                for family, species_data in self.result_data.items():
                    family_header = '{}\n{}\n{}\n'.format('-'*20, family, '-'*20)
                    score_file.write(family_header)    # an underlined heading for each family
                    family_scores = []  # necessary in order to sort in ascending order of score when writing
                
                    for species, (names, predictions, fermi_data, corr_count) in species_data.items():
                        plot_window.set_next_species(species)
                        
                        num_correct, num_total = corr_count['correct'], corr_count['total']
                        score = round(num_correct/num_total, 4)
                        family_scores.append((species, score))
                        
                        fermi_plot = (sorted(fermi_data, reverse=True), '{}, {}/{} correct'.format(species, num_correct, num_total), 'f')
                        summation_plot = ([iumsutils.average(column) for column in zip(*predictions)], 'Standardized Summation', 'p')
                        prediction_plots =  zip(predictions, names, tuple('p' for i in predictions))   # all the prediction plots                
                        all_plots = (fermi_plot, summation_plot, *prediction_plots)
                        
                        fermi_summary.append(fermi_plot)
                        self.adagraph(all_plots, 6, Path(self.file_dir, 'Result Plots', species+'.png'))  
                        if species in self.unfamiliars:
                            self.adagraph(all_plots, 6, Path('Condensed Unfamiliar Plots', species+'.png')) # make a copy of the results in a shared, accessible folder
                     
                    # NOTE: add averages buy family!!
                    family_scores.sort(key=lambda x : x[1], reverse=True)
                    for (species, score) in family_scores:
                        score_file.write('{} : {}\n'.format(species, score))
                        
            plot_window.set_next_species('Fermi Plot Summary')
            self.adagraph(fermi_summary, 5, Path(self.file_dir, 'Result Plots', 'Fermi Summary.png'))
            
            plot_window.destroy()
            messagebox.showinfo('Plotting Done!', 'Successfully converted NW output into plots')
        
if __name__ == '__main__':        
    main_window = tk.Tk()
    app = NIOBIUMS_App(main_window)
    main_window.mainloop()
