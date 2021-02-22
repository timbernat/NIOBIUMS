# GUI imports
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

# Custom imports
import iumsutils           # library of functions specific to my "-IUMS" class of IMS Neural Network applications
import plotutils           # library of custom plotting utilites which greatly simplify result output
import TimTkLib as ttl     # library of custom tkinter widgets I've written to make GUI assembly more straightforward

# Builtin imports (expect for matplotlib)
import json
from random import sample
from pathlib import Path
   
    
class NIOBIUMS_App:
    '''NIOBIUMS = NeuralWare I/O Bookend Interface for Unlabelled Mobility Spectra'''
    data_path = Path('Spectral Datasets') # this is the folder where NIOBIUMS will check and read data files
    
    def __init__(self, main):
        self.main = main
        self.main.title('NIOBIUMS v1.65-beta')
        
        self.quit_button =  tk.Button(self.main, text='Quit', padx=21, pady=27, underline=0, bg='red', command=self.quit)
        self.reset_button = tk.Button(self.main, text='Reset', padx=17, pady=2, underline=0, bg='orange', command=self.reset)
        
        self.main.bind('q', lambda event : self.quit())
        self.main.bind('r', lambda event : self.reset())
        
        self.quit_button.grid( row=0, column=1, sticky='s')
        self.reset_button.grid(row=2, column=1, padx=2, pady=2, sticky='s')

    #Frame 1
        self.data_file      = None   # initializing some parameters variables for later
        self.chem_data      = []
        self.species        = []
        self.families       = []
        self.family_mapping = {}
        self.species_count  = {}
        
        if not self.data_path.exists(): # make a folder if none exists
            self.data_path.mkdir()
        
        self.data_frame  = ttl.ToggleFrame(self.main, text='Select Data File to Read: ', padx=6, pady=5, row=0)     
        
        self.chosen_file = tk.StringVar()
        self.json_menu   = ttl.DynOptionMenu(self.data_frame, var=self.chosen_file, option_method=iumsutils.get_by_filetype,
                                           opargs=('.json', self.data_path), default='--Choose a JSON--', width=28, colspan=2)
        self.read_label     =  tk.Label(self.data_frame, text='Read Status:')
        self.read_status    = ttl.StatusBox(self.data_frame, on_message='JSON Read!', off_message='No File Read', row=1, col=1)
        self.refresh_button = tk.Button(self.data_frame, text='Refresh JSONs', underline=2, command=self.json_menu.update, padx=12)
        self.confirm_button = ttl.ConfirmButton(self.data_frame, padx=2, underline=0, command=self.import_data, row=1, col=2)
        
        self.refresh_button.grid(row=0, column=2)
        self.read_label.grid(row=1, column=0)
        
    #Frame 2
        self.species_frame = ttl.ToggleFrame(self.main, text='Set Learn/Test File Parameters:', padx=12, pady=5, row=1)      
        self.unfamiliars   = []
        self.file_dir      = None

        self.select_unfams    = tk.BooleanVar()
        self.split_prop_entry = ttl.LabelledEntry(self.species_frame, 'Set Proportion for Learn: ', tk.DoubleVar(), default=0.8)
        self.unfamiliar_check = tk.Checkbutton(self.species_frame, text='Unfamiliars?', underline=0, variable=self.select_unfams, command=self.further_sel)
        self.skip_to_plotting = tk.Button(self.species_frame, text='Replot Existing Results', padx=40, underline=7, command=self.choose_and_replot)
        self.splitting_button = tk.Button(self.species_frame, text='Perform Splitting', padx=2, underline=8, bg='deepskyblue2', command=self.separate_and_write)
        
        self.unfamiliar_check.grid(row=0, column=2, sticky='w')
        self.skip_to_plotting.grid(row=1, column=0, columnspan=2, sticky='w')
        self.splitting_button.grid(row=1, column=2, sticky='e')
        
    #Frame 3
        self.plotting_frame = ttl.ToggleFrame(self.main, text='Plot Training Results', padx=0, pady=0, row=2)

        self.species_label  = tk.Label(self.plotting_frame, text='Currently Plotting: ')
        self.curr_species   = tk.Label(self.plotting_frame, text='---')
        self.progress_label = tk.Label(self.plotting_frame, text='Plotting Progress: ')
        self.progress       = ttl.NumberedProgBar(self.plotting_frame, maximum=100, length=220, default=0, row=1, col=1)
        self.plot_button    = tk.Button(self.plotting_frame, text='Plot Training Results', padx=109, underline=0, bg='deepskyblue2', command=self.plot_nnr)
        
        self.species_label.grid( row=0, column=0)
        self.curr_species.grid(  row=0, column=1, sticky='w')
        self.progress_label.grid(row=1, column=0)
        #NumberedProgBar is already gridded
        self.plot_button.grid(   row=2, column=0, columnspan=2,sticky='e')
        
    #Misc/Other
        self.arrays = (self.chem_data, self.species, self.families, self.family_mapping, self.unfamiliars, self.species_count)
        self.frames = (self.data_frame, self.species_frame, self.plotting_frame)
        self.main.bind('<Key>', self.key_in_input) # activate internal conditional hotkey binding
        self.isolate(self.data_frame)
        self.lift() 
        
    #General Methods
    def lift(self):
        '''Bring GUI window to front of tabs'''
        self.main.attributes('-topmost', True)
        self.main.attributes('-topmost', False)
    
    def isolate(self, on_frame):
        '''Enable just one frame.'''
        for frame in self.frames:
            if frame == on_frame:
                frame.enable()
            else:
                frame.disable()   
    
    def prepare_folder(self, folder_path):
        '''File management utility, guarantees that the specified folder exists and is empty, performs overwrite checks as necessary'''
        if folder_path.exists():
            if any(folder_path.iterdir()): # if the directory is not empty
                if messagebox.askyesno('Duplicates Found', 'Folder with same data settings found;\nOverwrite old folder?'): # and user gives overwrite permission
                    try:
                        iumsutils.clear_folder(folder_path)
                    except PermissionError: # throw error if files cannot be properly overwritten due to still being open
                        messagebox.showerror('Permission Error', f'One or more files in {folder_path} are still open;\nPlease close all files and try again')
                        return
                else:
                    return # exit if user does not allow overwrite                  
        else:
            folder_path.mkdir(parents=True)
    
    def key_in_input(self, event):
        '''Hotkey binding wrapper for all frames - ensures actions are only available when the parent frame is enabled'''
        if self.data_frame.state == 'normal': # do not allow hotkeys to work if frame is disabled
            if event.char == 'f':
                self.json_menu.update()
            elif event.char == 'c':
                self.import_data()
        elif self.species_frame.state == 'normal':
            if event.char == 'e':
                self.choose_and_replot()
            elif event.char == 's':
                self.separate_and_write()
            elif event.char == 'u':
                self.unfamiliar_check.select()
                self.further_sel()
        elif self.plotting_frame.state == 'normal' and event.char == 'p': # do not allow hotkeys to work if frame is disabled
            self.plot_nnr()
    
    def reset(self):
        '''Reset the menu and internal variables to their original state'''   
        self.file_dir  = None
        self.data_file = None
        for array in self.arrays:
            array.clear()         
        
        self.read_status.set_status(False)
        self.json_menu.reset_default()
        self.split_prop_entry.reset_default()
        self.unfamiliar_check.deselect()

        self.progress.set_max(100)
        self.progress.reset()
        self.isolate(self.data_frame)
 
    def quit(self):
        '''Close the application, with confirm prompt'''
        if messagebox.askokcancel('Confirm Quit', 'Are you sure you want to close?'):
            self.main.destroy()
            
#Frame 1 (File selection) Methods     
    def import_data(self):
        '''Read in data based on the selected data file'''
        if self.chosen_file.get() == '--Choose a JSON--':
            messagebox.showerror('File Error', 'No JSON selected')
        else:
            self.data_file = Path(self.data_path/f'{self.chosen_file.get()}.json')
            json_data = iumsutils.load_chem_json(self.data_file)
            
            self.chem_data      = json_data['chem_data']
            self.species        = json_data['species']
            self.families       = json_data['families']
            self.family_mapping = json_data['family_mapping']
            self.species_count  = json_data['species_count']
            
            self.read_status.set_status(True)
            self.isolate(self.species_frame)
    
#Frame 2 (species selection and separation) methods
    def further_sel(self): 
        '''logic for selection of species to include in training'''
        self.unfamiliars.clear()
        if self.select_unfams.get():
            ttl.SelectionWindow(self.main, self.species_frame, self.species, self.unfamiliars, ncols=8)
    
    def separate_and_write(self):
        '''Separate the chem_data, based on the users selection of unfamiliars and split proportion, and write to test and learn files'''
        split_prop = self.split_prop_entry.get_value()
        split_complement = round(1 - split_prop, 4)   # rounding to 4 places should avoid float error for typical proportions (noted here for future debugging)
         
        # very crucially, the "0" branch of the and/or statment MUST be second, or the logic breaks down due to quirks in how these statments are parsed
        species_to_keep = {species : iter(sample([i >= (species not in self.unfamiliars and round(split_prop*count) or 0) # construct iterator of randomly dispersed bools for...
                                                         for i in range(count)], count)) # ...each species, such that the proportion of Trues rationally approximates the...
                                     for species, count in self.species_count.items()} # proportion specified to keep (or is just 0, if the species is denoted unfamiliar)
        
        training_desc = (self.select_unfams.get() and f'No {", ".join(self.unfamiliars)}' or 'Control Run') # create informative string about the set     
        self.file_dir = Path('Training Files',self.data_file.stem,f'{split_prop}-{split_complement} split, {training_desc}')
        self.prepare_folder(self.file_dir) # file management to ensure a file exists
   
        learn_labels, test_labels = [], []
        with open(self.file_dir/'TTT_testfile.txt', 'w') as test_file, open(self.file_dir/'LLL_learnfile.txt', 'w') as learn_file:    
            for instance in self.chem_data:               
                stringy_data = map(str, [*instance.spectrum, *instance.vector])  # unpack the data into a single long list of strings
                formatted_entry = '\t'.join(stringy_data) + '\n' #f'!{instance.name}\n' # tab-separate the data and append the name as a comment (!-delimited) with newline

                if next(species_to_keep[instance.species]):  # pull out terms from random bool iter assigned to each instance to determine where to place it
                    test_labels.append(instance.name)
                    test_file.write(formatted_entry)
                    self.species_count[instance.species] -= 1
                else:
                    learn_labels.append(instance.name)
                    learn_file.write(formatted_entry) 
                               
        with open(self.file_dir/'Test Labels.json', 'w') as test_labels_file, open(self.file_dir/'Learn Labels.json', 'w') as learn_labels_file: 
            json.dump(test_labels, test_labels_file)    # write the labels associated with each file to jsons for records and later access if replotting
            json.dump(learn_labels, learn_labels_file)
        messagebox.showinfo('File Creation Successful!', 'Files can be found in "Training Files" folder\n\nPlease perform training, then proceed to plotting')
        
        self.isolate(self.plotting_frame)
                
    def choose_and_replot(self):
        '''Allow the user to pick a folder from which to replot'''
        self.file_dir = Path(filedialog.askdirectory(initialdir='.\Training Files', title='Select folder with .nnr file'))
        self.isolate(self.plotting_frame)
          
# Frame 3
    def set_next_species(self, species):  
        '''For straightforwardly incrementing the menu progress bar with each new species'''
        self.curr_species.configure(text=species)
        self.progress.increment()
        self.main.update()
    
    def read_and_label_predictions(self):
        '''Reads in the assigned prediction values from the nnr, matches them to the names in the labels file, returns a zipped list of both'''
        predictions = {}
        with open(self.file_dir/'TTT_testfile_txt.nnr', 'r') as result_file, open(self.file_dir/'Test Labels.json', 'r') as test_labels_file:         
            for row, inst_name in zip(result_file, json.load(test_labels_file)):
                readable_row = [float(i) for i in row.split('\t')[1:]] # get rid of tabs, newlines, and other NW garbage output and convert to numerical values #ANCHOR
                vector = [int(i) for i in readable_row[:len(self.family_mapping)]]      
                aavs   = readable_row[len(self.family_mapping):]

                species, family = iumsutils.isolate_species(inst_name), iumsutils.get_family(inst_name)
                if self.family_mapping[family] != vector:
                    raise ValueError(f'NeuralWare has mislabelled {inst_name} ({vector} rather than {self.family_mapping[family]})')

                if not predictions.get(family):
                    predictions[family] = {}
                if not predictions[family].get(species):
                    predictions[family][species] = {}
                predictions[family][species][inst_name] = aavs
        
        return predictions
      
    def plot_nnr(self):
        #Method used to process and plot the test data from the .nnr after training
        if not Path(self.file_dir/'TTT_testfile_txt.nnr').exists(): 
            messagebox.showerror('No NNR File Present!', 'Please perform training before attempting plotting')
            return # terminate prematurely if no file is present
        
        result_dir = self.file_dir/'Result Plots' 
        self.prepare_folder(result_dir)

        unfam_dir = self.file_dir.parents[0]/'Condensed Unfamiliar Plots'
        if not unfam_dir.exists(): # ensure a condensed unfamiliar plot folder really exists
            unfam_dir.mkdir(parents=True)
        
        plotutils.Base_RC.unit_circle = plotutils.Mapped_Unit_Circle(self.family_mapping) # set base unit circle based on the current mapping
        predictions = self.read_and_label_predictions()
        self.progress.set_max(len(self.species)+1) # number of plots, plus the summaries (fermi plots and scores), hence + 1
        
        score_path = result_dir/'Scores.csv'
        score_path.touch()
        with score_path.open('w') as score_file:
            for family, species_dat in predictions.items():
                score_file.write(family)
                hotbit = self.family_mapping[family].index(1) # deduce hotbit from mapping and current species
                
                fam_scores = []
                for species, inst_dat in species_dat.items():
                    self.set_next_species(species) # remember to increment progressbar and update the current species
                    is_unfamiliar = species in self.unfamiliars
                    
                    panel = plotutils.Multiplot(nrows=2, span=3) # create the panel 
                    spectra = [instance.spectrum for instance in self.chem_data if instance.species == species] # pull out the spectra for the current species

                    panel.draw(plotutils.PWA_Plot(spectra, species), 0)
                    panel.draw(plotutils.Species_RC(predictions, species), 1)
                     
                    fermi_plot = plotutils.Fermi_Plot(predictions, species, hotbit) # fermi plot not created in-place in order to extract the score
                    panel.draw(fermi_plot, 2)
                    
                    panel.save(result_dir/species, close=not is_unfamiliar) # don't close the plot if the current species is an unfamiliar                   
                    if is_unfamiliar: # also plot the species' result in a shared folder if unfamiliar
                        panel.save(unfam_dir/species)  # make a copy of the results in a shared, accessible folder, close out plot
                    
                    score_file.write(f'\n{species}, {fermi_plot.score}')
                    fam_scores.append(fermi_plot.score)
                score_file.write(f'\nAVERAGE, {iumsutils.average(fam_scores)}')
                score_file.write('\n\n') # leave a gap between each family

        self.set_next_species('Summaries') 
        plotutils.single_plot(plotutils.Overlaid_Family_RC(predictions), result_dir/'Overall Summary', figsize=8)
        
        pred_path = result_dir/'Predictions.json'
        pred_path.touch()
        with pred_path.open('w') as pred_file: # save the hierarchically-organized predictions to a local file
            json.dump(predictions, pred_file)
    
        self.lift()
        self.curr_species.configure(text='Plotting Complete')
        messagebox.showinfo('Plotting Complete!', 'Successfully converted NW output into plots')
        
if __name__ == '__main__':        
    main_window = tk.Tk()
    app = NIOBIUMS_App(main_window)
    main_window.mainloop()
