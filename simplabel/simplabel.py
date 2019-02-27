import tkinter as tk
from tkinter.messagebox import askquestion
from PIL import Image,ImageTk
import os
from functools import partial
import pickle
import time
import sys


class ImageClassifier(tk.Frame):
    """
    Manually label images from a folder into arbitrary categories
    
    Parameters
    ----------
    parent : tkinter.TK()
        tkinter instance
    directory : string
        Directory to explore for the images to label (must contain only image files)
    categories : list[string]
        Disting categories to use for labelling

    Notable attributes
    -------
    labelled : dict(string: string)
        Dictionary containing the labels in the form {'image_name.jpg': label}
        This dict is saved to disk by the 'Save' button
    """

    def __init__(self, parent, directory, categories = None, *args, **kwargs):

        # Initialize frame
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.root = parent
        self.root.wm_title("Simplabel")

        # Window Dimensions
        self.winwidth = 1000
        self.imwidth = self.winwidth - 10
        self.imheight = int(self.imwidth // 1.5)

        #  Directory containing the raw images and saved dictionary
        self.folder = directory
        self.savepath = self.folder + "/labeled.pkl"
        self.labelpath = self.folder + "/labels.pkl"

        # Categories for the labelling task
        self.labels_from_file = False
        self.categories = categories
        self.initialize_labels()

        # Initialize data
        self.initialize_data()

        # Make a frame for global control buttons (at the top of the window)
        self.frame0 = tk.Frame(self.root, width=self.winwidth, height=10, bd=2)
        self.frame0.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Make a frame to display the image
        self.frame1 = tk.Frame(self.root, width=self.winwidth, height=self.imheight+10, bd=2)
        self.frame1.pack(side=tk.TOP)

        # Create a canvas for the image
        self.cv1 = tk.Canvas(self.frame1, width=self.imwidth, height=self.imheight, background="white", bd=1, relief=tk.RAISED)
        self.cv1.pack(in_=self.frame1)

        # Make a frame to display the labelling buttons (at the bottom)
        self.frame2 = tk.Frame(self.root, width=self.winwidth, height=10, bd=2)
        self.frame2.pack(side = tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Create the global buttons
        tk.Button(self.root, text='Exit', height=2, width=8, command =self.exit).pack(in_=self.frame0, side = tk.RIGHT)
        tk.Button(self.root, text='Reset', height=2, width=8, command =self.reset_session).pack(in_=self.frame0, side = tk.RIGHT)
        tk.Button(self.root, text='DELETE ALL', height=2, width=10, command =self.delete_saved_data).pack(in_=self.frame0, side = tk.RIGHT)

        tk.Button(self.root, text='Save', height=2, width=8, command =self.save).pack(in_=self.frame0, side = tk.LEFT)
        tk.Button(self.root, text='Previous', height=2, width=8, command =self.previous_image).pack(in_=self.frame0, side = tk.LEFT)

        # Create a button for each of the categories
        for idx, category in enumerate(self.categories):
            txt = category + " ({})".format(idx+1)
            tk.Button(self.root, text=txt, height=2, width=8, command = partial(self.classify, category)).pack(in_=self.frame2, fill = tk.X, expand = True, side = tk.LEFT)

        # Create the key bindings
        self.root.bind("<Key>", self.keypress_handler)
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)

        # Display the first image
        self.display_image()

    def initialize_labels(self):
        '''Loads labels from file if it exists or use labels passed as argument (these override any file defined labels).'''
        # Passed labels override any existing file
        if not self.categories:
            # Check for label file and load if it exists
            if os.path.isfile(self.labelpath):
                with open(self.labelpath,"rb") as f:
                    self.categories = pickle.load(f)
                self.labels_from_file = True
                print("Loaded categories from file: {}".format(self.categories))
            # Exit if no labels are found
            else:
                print("No categories provided. Exiting.")
                self.errorClose()
        # If labels are passed, use these and save them to file
        else:
            # Add default categories
            self.categories.append('Remove')
            print("Using categories passed as argument: {}".format(self.categories))
        

    def initialize_data(self):
        '''Loads existing data from disk if it exists and loads a list of unlabelled images found in the directory'''
        # Initialize dictionary
        if os.path.isfile(self.savepath):
            self.labeled = self.load_dict(self.savepath)
            print("Loaded existing dictionary from disk")
            # Check that the categories used in the dictionary are in self.categories
            if any([val not in self.categories for val in self.labeled.values()]):
                print("Labels in dictionary do not match passed categories")
                print("Labels in dictionary: {}".format(set(self.labeled.values())))
                print("Categories passed: {}".format(self.categories))
                self.errorClose()
        else:
            self.labeled = {}
            print("No dictionary found, initializing a new one")

        # All checks for label consistency are over, save labels to file if they were passed as arguments
        if not self.labels_from_file:
            with open(self.labelpath,'wb') as f:
                pickle.dump(self.categories, f)

        # Build list of images to classify
        self.image_list = []
        for d in os.listdir(self.folder):
            if d not in self.labeled and not d.endswith('.pkl'): 
                self.image_list.append(d)
        if len(self.image_list) == 0:
            print("No images found in directory.")
            self.errorClose()
        else:
            print("{} images ready to label".format(len(self.image_list)))

        # Initialize counter and get number of images   
        self.counter = 0
        self.max_count = len(self.image_list)-1

    def classify(self, category):
        '''Adds a directory entry with the name of the image and the label selected'''
        if self.counter > self.max_count:
            print("No more images to label")
        else:
            self.labeled[self.image_list[self.counter]] = category
            print('Label {} selected for image {}'.format(category, self.image_list[self.counter]))
            self.next_image()
    
    def previous_image(self, *args):
        '''Displays the previous image'''
        if self.counter > 0:
            self.counter += -1
            self.display_image()
        else:
            print("This is the first image, can't go back")
    
    def next_image(self, *args):
        '''Displays the next image'''
        if self.counter <= self.max_count:
            self.counter += 1
            self.display_image()
        else:
            print("No more images")
            self.display_end()

    def display_image(self):
        '''Displays the image corresponding to the current value of the counter'''
        if self.counter > self.max_count and self.max_count > -1:
            print("No more images")
            self.display_end()
        elif self.max_count == 0:
            print("No images to label")
            self.errorClose()
        else:
            self.im = Image.open("{}{}".format(self.folder + '/', self.image_list[self.counter]))
            if (self.imwidth-self.im.size[0])<(self.imheight-self.im.size[1]):
                width = self.imwidth
                height = width*self.im.size[1]/self.im.size[0]
            else:
                height = self.imheight
                width = height*self.im.size[0]/self.im.size[1]
            
            self.im.thumbnail((width, height), Image.ANTIALIAS)
            self.photo = ImageTk.PhotoImage(self.im)

            if self.counter == 0:
                self.cv1.create_image(0, 0, anchor = 'nw', image = self.photo)

            else:
                self.cv1.delete("all")
                self.cv1.create_image(0, 0, anchor = 'nw', image = self.photo)

    def display_end(self):
        '''Handles the exit when the labelling task is finished'''
        result = askquestion('No more images to label', 'Save before exiting?', icon = 'warning')
        if result == 'yes':
            self.save()
        self.quit()


    def keypress_handler(self,e):
        try:
            cat = int(e.char) - 1
            if cat in range(len(self.categories)):
                self.classify(self.categories[cat])
        except ValueError:
            if e.char == 's':
                self.save()
            elif e.char == 'q':
                self.exit()
            elif e.char == 'r':
                self.reset_session()
            else:
                pass
    
    def save(self):
        '''Save the labeled dictionary to disk'''
        self.dump_dict(self.labeled, self.savepath)
        print("Saved data to file")
    
    def load_dict(self, file):
        '''Read a pickeled dictionary from file'''
        with open(file,"rb") as f:
            return pickle.load(f)
    
    def dump_dict(self, dict, file):
        '''Pickle a dictionary to file'''
        with open(file, 'wb') as f:
            pickle.dump(dict, f)

    def reset_session(self):
        '''Deletes all labels from the current session and reload the images'''
        result = askquestion('Are you sure?', 'Delete data since last save?', icon = 'warning')
        if result == 'yes':
            print("Resetting session since last save and reinitializing date")
            self.labeled = {}
            self.initialize_data()
            self.display_image()
        else:
            pass
    
    def delete_saved_data(self):
        '''Deletes all labeles from session and saved data then reloads the images'''
        result = askquestion('Are you sure?', 'Delete all saved and session data?', icon = 'warning')
        if result == 'yes':
            print("Deleting all saved progress and reinitializing data")
            if os.path.isfile(self.savepath):
                os.remove(self.savepath)
            self.initialize_data()
            self.display_image()
        else:
            pass

    def exit(self):
        '''Cleanly exits the app'''
        result = askquestion('Save?', 'Do you want to save this session before leaving?', icon = 'warning')
        if result == 'yes':
            self.save()
        self.quit()

    def errorClose(self):
        '''Closes the window when the app encouters an error it cannot recover from'''
        print("Closing the app...")
        self.master.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk() 
    rawDirectory = "data/raw"
    categories = ['Crystal', 'Clear']
    MyApp = ImageClassifier(root, rawDirectory, categories)
    tk.mainloop()