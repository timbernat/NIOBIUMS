# GUI imports
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

# Custom imports
import r_iumsutils as iumsutils           # library of functions specific to my "-IUMS" class of IMS Neural Network applications
import TimTkLib as ttl     # library of custom tkinter widgets I've written to make GUI assembly more straightforward

# Builtin imports (expect for matplotlib)
import json, re  
from pathlib import Path
from shutil import rmtree
import matplotlib.pyplot as plt
   
    
class PlottingWindow:
    '''A window which displays plotting progress, was easier to subclass outside of the main GUI class'''
    def __init__(self, main, num_cycles):
        self.main = main
        self.plotting_window = tk.Toplevel(main)
        self.plotting_window.title('Plotting Progress')
        self.plotting_window.geometry('374x57')
        self.plotting_window.attributes('-topmost', True)
        
        # Status Printouts
        self.status_frame = ttl.ToggleFrame(self.plotting_window, '', padx=13)
        
        self.species_label =  tk.Label(self.status_frame, text='Currently Plotting: ')
        self.curr_species =   tk.Label(self.status_frame, text='---')
        self.progress_label = tk.Label(self.status_frame, text='Plotting Progress: ')
        self.progress =       ttl.NumberedProgBar(self.status_frame, total=num_cycles, length=240, default=1, row=1, col=1) 
        
        self.species_label.grid(  row=0, column=0)
        self.curr_species.grid(   row=0, column=1, sticky='w')
        self.progress_label.grid( row=1, column=0)
        #NumberedProgBar is already gridded
    
    def set_species(self, species):
        self.curr_species.configure(text=species)
        self.main.update()
        
    def set_next_species(self, species):  
        '''For straightforwardly incrementing progress with each new species'''
        self.set_species(species)
        self.progress.increment()
        
    def set_progress(self, cycle):
        self.progress.set_progress(cycle)
        self.main.update()
        
class NIOBIUMS_App:
    '''The Separation App itself. NIOBI-UMS = NeuralWare I/O Bookend Interface for Unlabelled Mobility Spectra'''
    def __init__(self, main):
        self.main = main
        self.main.title('NIOBI-UMS v1.3-beta')
        self.main.geometry('412x197')

        #Frame 1
        self.data_frame = ttl.ToggleFrame(self.main, text='Select JSON to Read: ', padx=6, pady=5, row=0)
        self.chosen_file, self.data_file = tk.StringVar(), None   
        self.chem_data, self.species, self.families, self.family_mapping, self.species_count = {}, [], [], {}, {}
        
        self.json_menu = ttl.DynOptionMenu(self.data_frame, var=self.chosen_file, option_method=iumsutils.get_by_filetype,
                                           opargs=('.json',), default='--Choose a JSON--', width=28, colspan=2)
        self.read_label =     tk.Label(self.data_frame, text='Read Status:')
        self.read_status =    ttl.StatusBox(self.data_frame, on_message='JSON Read!', off_message='No File Read', row=1, col=1)
        self.refresh_button = tk.Button(self.data_frame, text='Refresh JSONs', command=self.json_menu.update, padx=12)
        self.confirm_button = ttl.ConfirmButton(self.data_frame, padx=2, command=self.import_data, row=1, col=2)
        
        self.refresh_button.grid(row=0, column=2)
        self.read_label.grid(row=1, column=0)
        
        
        #Frame 2
        self.species_frame = ttl.ToggleFrame(self.main, text='Set Learn/Test File Parameters:', padx=14, pady=5, row=1)
        self.select_unfams = tk.BooleanVar()
        self.unfamiliars = []
        self.file_dir = None

        self.split_prop_entry = ttl.LabelledEntry(self.species_frame, 'Set Proportion for Learn: ', tk.DoubleVar(), default=0.8)
        self.unfamiliar_check = tk.Checkbutton(self.species_frame, text='Unfamiliars?', variable=self.select_unfams, command=self.further_sel)
        self.skip_to_plotting = tk.Button(self.species_frame, text='Skip to Plotting', padx=55, command=self.choose_and_replot)
        self.splitting_button = tk.Button(self.species_frame, text='Perform Splitting', padx=2, command=self.separate_and_write)
        
        self.unfamiliar_check.grid(row=0, column=2, sticky='w')
        self.skip_to_plotting.grid(row=1, column=0, columnspan=2, sticky='w')
        self.splitting_button.grid(row=1, column=2, sticky='w')
        
        
        #Frame 3
        self.plotting_frame = ttl.ToggleFrame(self.main, text='', padx=0, pady=0, row=2)
        self.result_data = {}
        
        self.plot_button = tk.Button(self.plotting_frame, text='Plot Training Results', padx=109, bg='dodger blue', command=self.plot_nnr)
        self.plot_button.grid(row=0, column=2, sticky='e')
        
        
        #Misc/Other
        self.exit_button =  tk.Button(self.main, text='Exit', padx=22, pady=27, bg='red', command=self.exit)
        self.reset_button = tk.Button(self.main, text='Reset', padx=17, pady=2, bg='orange', command=self.reset)
        
        self.exit_button.grid( row=0, column=1, sticky='s')
        self.reset_button.grid(row=2, column=1)
        
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
    
    def update_data_file(self):
        '''Used to assign the currently selected data file to an internal attribute'''
        self.data_file = Path(self.chosen_file.get())
    
    def reset(self):
        '''Reset the menu and internal variables to their original state'''   
        for array in (self.chem_data, self.species, self.families, self.family_mapping, 
                      self.unfamiliars, self.species_count, self.result_data):
            array.clear() 
        self.file_dir = None
        self.update_data_file()
        
        self.read_status.set_status(False)
        self.json_menu.reset_default()
        self.split_prop_entry.reset_default()
        self.unfamiliar_check.deselect()
        
        self.isolate(self.data_frame)
    
    def exit(self):
        '''Close the application, with confirm prompt'''
        if messagebox.askokcancel('Exit', 'Are you sure you want to close?'):
            self.main.destroy()
            
            
    #Frame 1 (File selection) Methods     
    def import_data(self):
        '''Read in data based on the selected data file'''
        self.update_data_file()
        if self.data_file == '--Choose a JSON--':
            messagebox.showerror('File Error', 'No JSON selected')
        else:
            with open(self.data_file) as json_file:
                self.chem_data, self.species, self.families, self.family_mapping, spectrum_size,\
                self.species_count, family_count = json.load(json_file).values() # spectrum size and family count are discarded after function is run (not needed)
            self.read_status.set_status(True)
            self.isolate(self.species_frame)
    
    
    #Frame 2 (species selection and separation) methods
    def further_sel(self): 
        '''logic for selection of speciess to include in training'''
        self.unfamiliars.clear()
        if self.select_unfams.get():
            ttl.SelectionWindow(self.main, self.species_frame, '960x190', self.species, self.unfamiliars, ncols=8)
    
    def separate_and_write(self):
        '''Separate the chem_data, based on the users selection of unfamiliars and split proportion, and write to test and learn files'''
        split_proportion = self.split_prop_entry.get_value()
        split_complement = round(1 - split_proportion, 4)   # rounding to 4 places should avoid float error for typical proportions (noted here for future debugging)
        
        kept_species_count = {species : (species not in self.unfamiliars and round(split_proportion*count) or 0) # OR must be in this order; everything is familiar if 0 comes first
                                    for species, count in self.species_count.items()} # set number of instances of each species to keep to 0 if they are unfamiliars... 
                                                                                      # ...(i.e not kept) or to the nearset interger to the proportion specified otherwise
        if self.select_unfams.get():   # if unfamiliars have been chosen
            training_desc = f'No {", ".join(self.unfamiliars)}'  
        else:
            training_desc = 'Control Run'
        self.file_dir = Path('Training Files',self.data_file.stem,f'{split_proportion}-{split_complement} split, {training_desc}')

        if self.file_dir.exists():   # prompt user to overwrite file if one already exists
            if messagebox.askyesno('Duplicates Found', 'Folder with same data settings found;\nOverwrite old folder?'):
                rmtree(self.file_dir, ignore_errors=True)
            else:
                return  #terminate prematurely if overwrite permission is not given
        try:
            self.file_dir.mkdir(parents=True)
        except PermissionError: # catch the exception wherein mkdir fails because the folder is inadvertently open
            messagebox.showerror('Permission Error', f'Couldn\'t rewrite folders while {self.file_dir} was open! \nPlease click "Perform Splitting" again')
            return    
            
        learn_labels, test_labels = [], []
        with open(self.file_dir/'TTT_testfile.txt', 'w') as test_file, open(self.file_dir/'LLL_learnfile.txt', 'w') as learn_file:    
            for species, instances in self.chem_data.items():               
                for instance, (spectrum, vector) in instances.items():  
                    stringy_data = map(str, [*spectrum, *vector]) # unpack the data into a single long list of strings
                    formatted_entry = '\t'.join(stringy_data) + '\n' # tab-separate the stringy data and follow it with a newline for readability

                    if self.species_count[species] > kept_species_count[species]:  # if the current amount of a species present is greater than the amount we'd like to keep
                        test_labels.append(instance)
                        test_file.write(formatted_entry)
                        self.species_count[species] -= 1
                    else:
                        learn_labels.append(instance)
                        learn_file.write(formatted_entry) 
                               
        with open(self.file_dir/'Test Labels.json', 'w') as test_labels_file, open(self.file_dir/'Learn Labels.json', 'w') as learn_labels_file: 
            json.dump(test_labels, test_labels_file)    # write the labels associated with each file to jsons for records and later access if replotting
            json.dump(learn_labels, learn_labels_file)
        messagebox.showinfo('File Creation Successful!', 'Files can be found in "Training Files" folder\n\nPlease perform training, then proceed to plotting')
        
        self.isolate(self.plotting_frame)
                
    def choose_and_replot(self):
        '''Allow the user to pick a folder from which to replot'''
        self.file_dir = Path(filedialog.askdirectory(initialdir='\Training Folders', title='Select folder with .nnr file'))
        self.isolate(self.plotting_frame)
        
    # Frame 3
    def plot_nnr(self):
        '''Method used to extract the data from the .nnr file created post-evalutaion, piar the the data with the
        correct species in the test names file, and plot the data in an identical manner to PLATIN-UMS results'''
        
        if not Path(self.file_dir/'TTT_testfile_txt.nnr').exists():
            messagebox.showerror('No NNR File Present!', 'Please perform training before attempting plotting')
            return # show error prompt and do nothing if no nnr file exists (i.e. training has not occurred)

        self.result_data = {family : # build up an empty dict (organized by family and species) to populate with data and then unpack for plotting/scores
                                {species : [ [], [], [], 0 ]
                                 for species in self.chem_data.keys() 
                                     if iumsutils.get_family(species) == family} 
                            for family in self.family_mapping.keys()}

        with open(self.file_dir/'Test Labels.json', 'r') as test_labels_file, open(self.file_dir/'TTT_testfile_txt.nnr', 'r') as result_file:
            test_labels, nnr_data = json.load(test_labels_file), [row for row in result_file] # read in results and corresponding labels
            
        for instance, row in zip(test_labels, nnr_data): # attach the names to the appropriate plaintext data and iterate
            names, predictions, fermi_data, nc = species_data = self.result_data[iumsutils.get_family(instance)][iumsutils.isolate_species(instance)]
            
            row_data = [float(i) for i in re.split('\t|\n', row)[1:-1]]  # remove tabs and newlines from nnr rows and convert them to numerical data
            vector, aavs = row_data[:5], row_data[5:],  # first five values in each row are the onehot vector, last 5 are the predictions values 
            target = aavs[vector.index(1)] # prediction value that the model has assigned to the actual identity of the instance
            
            num_correct = 0
            names.append(instance)
            predictions.append(aavs)
            fermi_data.append(target)
            if target == max(aavs):
                species_data[3] += 1 #TEMPORARY while I figure out why lists integers are suddenly immutable
        
        result_dir = self.file_dir/'Result Plots'
        if result_dir.exists():   # prompt user to overwrite file if one already exists
            if messagebox.askyesno('Duplicates Found', 'Plot folder already exists; Overwrite?'):
                rmtree(result_dir, ignore_errors=True)
            else:
                return  #terminate prematurely if overwrite permission is not given
        try:
            result_dir.mkdir()
        except PermissionError: # catch the exception wherein mkdir fails because the folder is inadvertently open
            messagebox.showerror('Permission Error', f'{result_dir} cannot be overwritten while open!\n Please click "Plot Results" again')
            return 
    
        plot_window = PlottingWindow(self.main, num_cycles=len(self.chem_data)+1) # increase number of plots by 1 to account for the extra Fermi Plot summary
        with open(result_dir/'Scores.txt', 'w') as score_file:                  
            fermi_summary = []
            
            for family, species_data in self.result_data.items():
                family_header = f'{"-"*20}\n{family}\n{"-"*20}\n' # an underlined heading for each family
                score_file.write(family_header)    
                family_scores = []  # necessary in order to sort in ascending order of score when writing

                for species, (names, predictions, fermi_data, num_correct) in species_data.items():
                    plot_window.set_next_species(species)

                    num_total = len(predictions) # NOTE!! must do this here, as after prepending the summary, all scores will be one longer than they should be
                    score = round(num_correct/num_total, 4) # for future, consider an alternate way of counting totals (likely once num_correct gets sorted out)
                    family_scores.append((species, score))
                    
                    fermi_data.sort(reverse=True)
                    try:
                        fermi_data = iumsutils.normalized(fermi_data)
                    except ZeroDivisionError: # if all data have the same value (e.g all 1.0), max=min and min/max normalization will fail
                        pass                  # skip over the set if this is the case               
                    fermi_plot = (fermi_data, f'{species}, {num_correct}/{num_total} correct', 'f')

                    predictions.insert(0, [iumsutils.average(column) for column in zip(*predictions)]) # prepend standardized sum of predictions to predictions
                    names.insert(0, 'Standardized Summation')                                          # prepend label to the above list to the titles list
                    prediction_plots = [ ((self.family_mapping.keys(), prediction), name, 'p') for name, prediction in zip(names, predictions) ] # all the prediction plots 
                    
                    all_plots = (fermi_plot, *prediction_plots)

                    fermi_summary.append(fermi_plot)
                    iumsutils.adagraph(all_plots, save_dir=result_dir/species)  
                    if species in self.unfamiliars:
                        unfam_dir = Path(self.file_dir.parent,'Condensed Unfamiliar Plots')
                        if not unfam_dir.exists(): # ensure a condensed unfam plot folder really exists
                            unfam_dir.mkdir(parents=True)
                        iumsutils.adagraph(all_plots, save_dir=unfam_dir/species) # make a copy of the results in a shared, accessible folder

                family_scores.sort(key=lambda x : x[1], reverse=True)
                family_scores.append( ('AVERAGE', iumsutils.average([score for (species, score) in family_scores], precision=4)) ) #note the average method does not accept generators
                for (species, score) in family_scores:
                    score_file.write(f'{species} : {score}\n')

        plot_window.set_next_species('Fermi Plot Summary')
        iumsutils.adagraph(fermi_summary, ncols=5, save_dir=result_dir/'Fermi Summary.png')

        plot_window.plotting_window.destroy()
        self.main.attributes('-topmost', True)
        self.main.attributes('-topmost', False) # temporarily bring main window to the forefront
        messagebox.showinfo('Plotting Done!', 'Successfully converted NW output into plots')
        
if __name__ == '__main__':        
    main_window = tk.Tk()
    app = NIOBIUMS_App(main_window)
    main_window.mainloop()
