import argparse
import tkinter as tk
from tkinter.messagebox import askquestion, askokcancel, showwarning
from tkinter import simpledialog, filedialog
from PIL import Image, ImageTk
import os
from functools import partial
import pickle
import time
import sys
import logging
import random
import getpass
import math


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
    verbose : int
        Logging level, 0: WARNING, 1: INFO, 2: DEBUG
    username : str
        Username to be used for multi-user mode
    autoRefresh : int
        Interval in seconds between auto-save and auto-refresh of master dict actions (0 to disable)
    bResetLock: bool
        When true, resets the lock that prevents multiple users from using the same username
    bRedundant: bool
        When true, other labeler's selections are not displayed.

    Notable outputs
    -------
    labelled_user.pkl : pickled dict(string: string)
        Dictionary containing the labels in the form {'relative/path/image_name.jpg': label}
        This dict is saved to disk by the 'Save' button
    """

    def __init__(self, parent, directory=None, categories=None, verbose=0, username=None,
                 autoRefresh=60, bResetLock=False, bRedundant=False, *args, **kwargs):

        # Initialize frame
        tk.Frame.__init__(self, parent, *args, **kwargs)

        # Initialize logger
        if verbose == 1:
            logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
        elif verbose >= 2:
            logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
        else:
            logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')

        self.root = parent
        self.root.wm_title("Simplabel")
        self.root.protocol('WM_DELETE_WINDOW', self.exit)
        self.gotLock = False

        # Supported image file formats (all extensions supported by PIL should work)
        self.supported_extensions = ['jpg', 'png', 'gif', 'jpeg ', 'eps', 'bmp', 'tiff', 'bmp',
                                     'icns', 'ico', 'spi',]

        # Define colors to be used for users
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2',
                       '#7f7f7f', '#bcbd22', '#17becf']

        # Screen Dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        logging.debug("Detected screen dimensions %d x %d", self.screen_width, self.screen_height)

        # Window Dimensions
        self.winwidth = min([800, int(0.7*self.screen_width)])
        self.imwidth = self.winwidth - 10
        self.imheight = min([int(self.imwidth // 1.5), int(0.9*self.screen_height)])
        self.root.geometry("{}x{}".format(self.winwidth, self.imheight+80))

        #  Directory containing the raw images
        if directory:
            self.folder = directory
        else:
            logging.info("No directory passed. Please select a directory...")
            response = filedialog.askdirectory(title="Select image directory",
                                               initialdir=os.getcwd(), mustexist=True)
            if os.path.isdir(response):
                self.folder = response
            else:
                logging.warning("Invalid or no directory passed. Closing the app.")
                self.errorClose()

        # Directory containing the labels
        self.labelpath = self.folder + "/labels.pkl"

        # Initialize state variables
        self.saved = True
        self.reconcileMode = False
        self.reconciledLabelsDict = None
        self.redundantMode = bRedundant
        if self.redundantMode:
            logging.warning("Redundant Mode - Other labeler's selections won't be displayed.")

        # Initialize a refresh timestamp and refresh interval for auto-save and auto-refresh
        self.saveTimestamp = time.time()
        self.saveInterval = autoRefresh
        self.refreshTimestamp = time.time()
        self.refreshInterval = autoRefresh

        # Find all labelers (other users)
        self.users = self.get_all_users()
        logging.info("Existing users: {}".format(self.users))

        # Assign a color for each user
        self.userColors = {}
        for user in self.users:
            self.userColors[user] = self.user_color_helper(user)
        self.userColors['master'] = '#3E4149'

        # Set the username for the current session
        if isinstance(username, str):
            # Sanitize: lowercase and remove spaces
            sanName = self.sanitize_user_name(username)
            # Check that username is not reserved
            if sanName == 'master':
                logging.error("Username 'master' is reserved.")
                newName = input("Please choose another name: ")
                sanName = self.sanitize_user_name(newName)
            self.username = sanName
            logging.info("Username: {}".format(self.username))
        else:
            try:
                username = self.sanitize_user_name(getpass.getuser())
                logging.info("No username passed, using system username: {}".format(username))
            except:
                username = "guest"
                logging.warning("No username passed, saving as guest")
            finally:
                self.username = username

        # Choose a color for the user and make sure user is in self.users
        if self.username in self.users:
            self.userColor = self.userColors[self.username]
        else:
            self.users.append(self.username)
            self.userColor = self.user_color_helper(self.username)
            self.userColors[self.username] = self.userColor

        # Initialize and check lock
        self.lock = FsLock(self.folder, self.username)
        try:
            self.lock.acquire()
        except:
            if bResetLock:
                logging.warning("Overriding the lock, this should only be used if you are certain \
                                no other user is using the same username.")
                self.lock.release()
                self.lock.acquire()
            else:
                logging.warning("The app is already in use with this username ({}). Please choose \
                                another username and restart.".format(self.username))
                logging.warning("If you are certain that is not the case, restart the app with \
                                 the flag --reset-lock")
                self.errorClose()

        self.gotLock = True

        # Directory containing the saved labeled dictionary
        self.savepath = self.folder + "/labeled_" + self.username +".pkl"

        # Initialize UI
        self.initialize_ui()

        # Categories for the labelling task
        self.labels_from_file = False
        self.categories = categories
        self.initialize_labels()

        # Initialize data
        self.initialize_data()

        # Create a button for each of the categories
        self.draw_label_buttons()

        # Display the first image
        self.display_image()

    ##############################
    ### Initializing methods #####
    ##############################

    def initialize_ui(self):
        '''Initialize UI with buttons and canvas for image'''

        # Make a frame for navigation buttons (at the top of the window)
        self.frame0 = tk.Frame(self.root, height=10, bd=2)
        self.frame0.pack(side=tk.TOP, fill=tk.X)

        # Make a frame to display the image
        self.frame1 = tk.Frame(self.root, highlightthickness=0)
        self.frame1.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        self.frame1.bind("<Configure>", self.responsiveCanvas)

        # Create a canvas for the image
        self.cv1 = tk.Canvas(self.frame1, background="white", relief=tk.RAISED, highlightthickness=0)
        self.cv1.pack(in_=self.frame1, fill=tk.BOTH, expand=tk.YES)

        # Placeholder for the label button frame
        self.labelFrameList = None

        # Create the key bindings
        self.root.bind("<Key>", self.keypress_handler)
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)

        # Create the navigation buttons
        self.firstButton = tk.Button(self.root, text='|<<', height=2, width=3, command=self.goto_first_image)
        self.firstButton.pack(in_=self.frame0, side=tk.LEFT)
        self.prevButton = tk.Button(self.root, text='<', height=2, width=3, command=self.previous_image)
        self.prevButton.pack(in_=self.frame0, side=tk.LEFT)
        self.nextButton = tk.Button(self.root, text='>', height=2, width=3, command=self.next_image)
        self.nextButton.pack(in_=self.frame0, side=tk.LEFT)
        self.nextUnlabeledButton = tk.Button(self.root, text='>?', height=2, width=3, wraplength=80, command=self.goto_next_unlabeled)
        self.nextUnlabeledButton.pack(in_=self.frame0, side=tk.LEFT)
        self.buttonOrigColor = self.firstButton.config()['highlightbackground'][-1]
        self.buttonBgOrigColor = self.firstButton.config()['background'][-1]
        self.lastButton = tk.Button(self.root, text='>>|', height=2, width=3, command=self.goto_last_image)
        self.lastButton.pack(in_=self.frame0, side=tk.LEFT)

        # Create the user action buttons
        self.saveButton = tk.Button(self.root, text='Save', height=2, width=8, command=self.save)
        self.saveButton.pack(in_=self.frame0, side=tk.LEFT)
        tk.Button(self.root, text='Exit', height=2, width=8, command=self.exit).pack(in_=self.frame0, side=tk.RIGHT)
        self.masterButton = tk.Button(self.root, text='Make Master', height=2, wraplength=55, width=8, command=self.make_master)
        self.masterButton.pack(in_=self.frame0, side=tk.RIGHT)
        self.reconcileButton = tk.Button(self.root, text='Reconcile', wraplength=80, height=2, width=8, command=self.reconcile)
        self.reconcileButton.pack(in_=self.frame0, side=tk.RIGHT)

        # Disable Reconcile and Make Master in Redundant mode
        if self.redundantMode:
            self.reconcileButton.config(state=tk.DISABLED)
            self.masterButton.config(state=tk.DISABLED)

        # Create a textbox for the current image information
        self.infoText = tk.Text(self.root, height=2, width=65, wrap=None)
        self.infoText.pack(in_=self.frame0)
        self.infoText.tag_config("c", justify=tk.CENTER)
        self.infoText.tag_config("r", foreground="#8B0000")
        self.infoText.tag_config("u", underline=1, foreground=self.userColor)

        ## Create user color tags
        for (user, color) in self.userColors.items():
            self.infoText.tag_config("{}Color".format(user), foreground=color)

        ## Display all labelers' names
        self.update_users_displayed()

    def initialize_labels(self):
        '''Loads labels from file if it exists else loads labels passed as argument.'''

        # If a label file is found, use that and issue a warning that passed categories are ignored
        if os.path.isfile(self.labelpath):
            if self.categories:
                logging.warning("Found label file, ignoring labels passed as argument.")
            with open(self.labelpath, 'rb') as f:
                loadedLabels = pickle.load(f)
            # Sanitize loaded labels
            sanLabels = [self.sanitize_label_name(label) for label in loadedLabels]
            # Remove duplicates
            self.categories = list(dict.fromkeys(sanLabels))
            logging.info("Loaded labels from file: {}".format(self.categories))

        # If no file is found and there are passed arguments, sanitize and use them
        elif self.categories:
            sanCategories = []
            for category in self.categories:
                sanCategories.append(self.sanitize_label_name(category))
            self.categories = sanCategories
            logging.info("Using labels passed as argument: {}".format(self.categories))

            # Save labels to file
            if not self.labels_from_file:
                with open(self.labelpath, 'wb') as f:
                    pickle.dump(self.categories, f)

        # If no file and no categories passed, leave categories as an empty list
        else:
            self.categories = []

    def initialize_data(self):
        '''Loads existing data from disk if it exists and loads a list of unlabelled images found in the directory'''
        # Initialize current user's dictionary (Note: it might not exist yet)
        if os.path.isfile(self.savepath):
            self.labeled = self.load_dict(self.savepath)
            logging.info("Loaded existing dictionary from disk")
        else:
            self.labeled = {}
            logging.info("No dictionary found, initializing a new one")

        # Load data from all users
        self.update_all_dict()

        # Build list of images to classify
        self.image_list = []

        ## If the directory contains at least 1 image, process only this directory
        list_image_files = [d for d in os.listdir(self.folder) if
                            d.split('.')[-1].lower() in self.supported_extensions]
        if len(list_image_files) > 0:
            labeledByCurrentUser = []
            labeledByOtherUser = []
            toLabel = []
            for img in list_image_files:
                if img in self.labeled:
                    labeledByCurrentUser.append(img)
                elif img in self.allLabeledDict:
                    labeledByOtherUser.append(img)
                else:
                    toLabel.append(img)
        ## Otherwise, list and check subdirectories
        else:
            logging.info("No image files in main directory, searching sub-directories...")
            labeledByCurrentUser = []
            labeledByOtherUser = []
            toLabel = []
            sub_folder_list = [dirName for dirName in next(os.walk(self.folder))[1]
                               if not dirName.startswith('.')]
            for dirName in sub_folder_list:
                dir_path = os.path.join(self.folder, dirName)
                list_image_files = [d for d in os.listdir(dir_path)
                                    if d.split('.')[-1].lower() in self.supported_extensions]
                for img in list_image_files:
                    imgPath = dirName + '/' + img
                    if imgPath in self.labeled:
                        labeledByCurrentUser.append(imgPath)
                    elif imgPath in self.allLabeledDict:
                        labeledByOtherUser.append(imgPath)
                    else:
                        toLabel.append(imgPath)

        # Images that are already labeled are concatenated with the ones labeled by the current user
        #  last to enable them to review their own labelling
        alreadyLabeled = labeledByOtherUser + labeledByCurrentUser

        # Initialize counter at the numer of already labeled images
        self.counter = len(alreadyLabeled)

        # Add already labeled images first, images to label are shuffled
        random.seed() # Reset the random seed
        random.shuffle(toLabel) # Shuffle the list in place
        self.image_list = alreadyLabeled + toLabel

        # Check that there is at least one image
        if len(self.image_list) == 0:
            logging.warning("No images found in directory.")
            self.errorClose()
        else:
            logging.info("Found {} images under the directory: {}".format(
                len(self.image_list), self.folder if '/' not in self.folder else self.folder.split('/')[-1]))
            logging.info("{} images left to label".format(len(self.image_list)-self.counter))

        # Get number of images
        self.max_count = len(self.image_list)-1

    ##############################
    ### Core functionality #######
    ##############################

    def classify(self, category):
        '''Adds a directory entry with the name of the image and the label selected'''

        if self.reconcileMode:

            img = self.image_list[self.counter]

            # Update reconciledLabelsDict
            self.reconciledLabelsDict[img] = category

            if self.saved:
                self.saved = False

            self.next_image()

        else:
            self.labeled[self.image_list[self.counter]] = category
            logging.info('Label {} selected for image {}'.format(category, self.image_list[self.counter]))
            if self.saved: # Reset saved status
                self.saved = False

            # If it is time to refresh the master and not in reconcile mode, do that
            # Note: after the refresh, the counter will be at the next unlabeled position
            if self.refreshInterval != 0 and (time.time() - self.refreshTimestamp > self.refreshInterval):
                logging.debug("classify - Triggered auto-refresh")
                self.refreshTimestamp = time.time()
                self.refresh_all_dict()
                self.display_image()
            else:
                self.next_image()

    def make_master(self):
        '''Reconcile conflicting labels and make a master dictionary'''

        # Refresh
        # Prepare lists of imgs, dump labeledAgree in masterdict
        # Enter reconcile mode and change user to 'master'
        # Display 'Master Mode'
        # After reconciliation, save master dict.

        # Refresh user list and allLabeledDict and sort labeled images
        # Note: sort_conflictinh_imgs refreshes the users and allLabeledDict
        self.save()
        (_, labeledDisagreed, toLabel) = self.sort_conflicting_imgs()

        # Check if there are any disagreed labels, enter reconcile mode and return if there are
        if len(labeledDisagreed) != 0:
            showwarning("Reconciliation needed", "Some images have conflicting labels, \
                         please reconcile them and try again.")
            self.reconcile()
            return
        # Check to see whether there are images left to label, ask user if they want to proceed anyway
        elif len(toLabel) != 0:
            response = askquestion("Unlabeled images", "Some images have not been labeled yet, \
                                    do you want to proceed anyway?")
            if response == 'no':
                return

        # Make a master dictionary
        masterDict = {}

        for img in self.allLabeledDict:
            masterDict[img] = next(iter(self.allLabeledDict[img].values())) # any value will do since they all agree

        # Save the master dictionary to disk
        logging.info('Saved the master dictionary to disk.')
        self.dump_dict(masterDict, self.folder + '/labeled_master.pkl')

        # Change the button color
        self.masterButton.config(highlightbackground='#3E4149', bg='#3E4149')

    def reconcile(self):
        '''Display images with disagreed labels for reconciliation'''

        # Turn on Reconcile Mode
        if self.reconcileMode == False:

            # Check locks and return if a lock a asserted.
            for user in self.users:
                if user != self.username:
                    logging.debug("reconcile - checking lock for user {}".format(user))
                    lock = FsLock(self.folder, user)
                    if lock.is_locked():
                        logging.warning("{} is logged in the app, cannot reconcile unless all users have closed the app.".format(user))
                        return

            # Must save before starting reconcile mode
            if not self.saved:
                result = askokcancel('Save?', 'Results must be saved before entering reconciliation', icon='warning')
                if result:
                    self.save()
                else:
                    return

            # Enable recondile Mode (autoRefresh off)
            self.reconcileMode = True

            # Change button text and status
            self.reconcileButton.config(text="Back", highlightbackground='#3E4149', bg='#3E4149')

            # Rebuild the image list
            (labeledAgreed, labeledDisagreed, toLabel) = self.sort_conflicting_imgs()

            # Initialize an empty reconciledLabelsDict
            self.reconciledLabelsDict = {}

            # Setup the counter, image_list and display the next image
            self.counter = len(labeledAgreed)
            self.image_list = labeledAgreed + labeledDisagreed + toLabel
            logging.info(f"Reconcile Mode - {len(labeledAgreed)} images with agreed labels, {len(labeledDisagreed)} \
                           images with disagreed labels, {len(toLabel)} images to label")
            self.display_image()

        # Turn off Reconcile mode
        else:
            # Must save before going back to normal mode
            if not self.saved:
                result = askquestion('Save?', 'Do you want to save the reconciliation results?', icon='warning')
                if result:
                    self.save()
                else:
                    return

            # Disable reconcile mode
            self.reconcileMode = False

            # Change button back
            self.reconcileButton.config(text="Reconcile", highlightbackground=self.buttonOrigColor, bg=self.buttonBgOrigColor)

            # Destroy reconciledLabelsDict
            self.reconciledLabelsDict = None

            # Update user list and master dict and go back to next unlabeled image
            self.labeled = self.load_dict(self.savepath)
            self.refresh_all_dict()
            logging.info("Labeling Mode")
            self.display_image()

    ##############################
    ### GUI Updating #############
    ##############################

    def draw_label_buttons(self):
        '''Displays a button for each label in the passed frame after emptying it'''

        # Destroy the frames
        if self.labelFrameList:
            for frame in self.labelFrameList:
                frame.destroy()

        # Create frames to pack the label buttons
        if self.categories:
            n_labels = len(self.categories)
            n_rows = (n_labels) // 4 + 1 # Each row can contain up to 4 labels
        
            self.labelFrameList = []

            # Make frames to display the labelling buttons (at the bottom)
            for i in range(n_rows):
                self.labelFrameList.append(tk.Frame(self.root, height=10, bd=2))
                self.labelFrameList[i].pack(side = tk.BOTTOM, fill=tk.X)

            # Create and pack a button for each label
            self.catButton = []
            for idx, category in enumerate(self.categories):
                txt = category + " ({})".format(idx+1)
                self.catButton.append(tk.Button(self.root, text=txt, height=2, width=8, command = partial(self.classify, category)))
                self.catButton[idx].pack(in_=self.labelFrameList[idx//4], fill = tk.X, expand = True, side = tk.LEFT)

            self.addCatButton = tk.Button(self.root, text='+', height=2, width=3, command = self.add_label)
            self.addCatButton.pack(in_=self.labelFrameList[-1], side = tk.LEFT)

        # When there are no labels yet, create a single frame to pack the "+" button in
        else:
            self.catButton = [] # Initialize an empty list
            self.labelFrameList = [tk.Frame(self.root, height=10, bd=2)]
            self.labelFrameList[0].pack(side = tk.BOTTOM, fill=tk.X)

            self.addCatButton = tk.Button(self.root, text='+', height=2, width=3, command = self.add_label)
            self.addCatButton.pack(in_=self.labelFrameList[-1], side = tk.LEFT, fill=tk.X, expand=tk.YES)
        
    def update_users_displayed(self):

        if self.redundantMode:
            ## Print the name of the current user 
            self.infoText.config(state=tk.NORMAL)
            self.infoText.delete('2.0', '2.end')
            self.infoText.insert('2.0', "\nRedundant Mode - ", 'c')
            self.infoText.insert(tk.END, "{}".format(self.username), ('c', '{}Color'.format(self.username), 'u'))

        else:
            ## Print the name of the current user 
            self.infoText.config(state=tk.NORMAL)
            self.infoText.delete('2.0', '2.end')
            self.infoText.insert('2.0', "\nLabelers: ", 'c')
            self.infoText.insert(tk.END, "{}".format(self.username), ('c', '{}Color'.format(self.username), 'u'))

            ## Print the names of other labelers
            for user in self.users:
                if user != self.username:
                    self.infoText.insert(tk.END, ", ", ('c',))
                    self.infoText.insert(tk.END, "{}".format(user), ('c', '{}Color'.format(user)))

            ## Disable the textbox
            self.infoText.config(state=tk.DISABLED)

    def display_image(self):
        '''Displays the image corresponding to the current value of the counter'''

        # If the counter overflows, go back to the last image
        if self.counter > self.max_count and self.max_count > -1:
            logging.debug("display_image - Counter overflowed")
            self.counter = self.max_count
            self.display_image()
        # If there are no images to label, exit
        elif self.max_count == 0:
            logging.warning("No images to label")
            self.errorClose()
        else:
            img = self.image_list[self.counter] # Name of current image
            self.im = Image.open("{}{}".format(self.folder + '/', img))

            #Resize the image to fit nicely in the frame
            if (self.im.size[0] > self.imwidth) or (self.im.size[1] > self.imheight):
                # If the image is larger than the frame, rescale it to fit
                if (self.imwidth / self.imheight) < (self.im.size[0] / self.im.size[1]):
                    # Image sticks out more in width than in height, set the width and scale the height
                    width = int(self.imwidth)
                    height = int(width*self.im.size[1]/self.im.size[0])
                else:
                    height = int(self.imheight)
                    width = int(height*self.im.size[0]/self.im.size[1])

                self.im.thumbnail((width, height), Image.ANTIALIAS)
            
            elif (self.im.size[0] * 2 > self.imwidth) or (self.im.size[1] * 2 > self.imheight):
                logging.debug("Resizing - Image is within 50% of frame size, resizing to full frame size")
                # If the image is within 50% of the frame size, resize it to fill the frame
                if (self.imwidth / self.imheight) < (self.im.size[0] / self.im.size[1]):
                    # Image aspect ratio smaller than frame, set the width and scale the height
                    width = int(self.imwidth)
                    height = int(width*self.im.size[1]/self.im.size[0])
                else:
                    height = int(self.imheight)
                    width = int(height*self.im.size[0]/self.im.size[1])
                
                self.im = self.im.resize((width, height), resample = Image.BICUBIC)

            elif (self.im.size[0] * 2 < self.imwidth) and (self.im.size[1] * 2 < self.imheight):
                logging.debug("Resizing - Image is smaller than 50% of frame size, resizing")
                # If the image is very small, resize it up to 2x
                width = int(self.im.size[0] * 2)
                height = int(self.im.size[1] * 2)

                self.im = self.im.resize((width, height), resample = Image.BICUBIC)
                
            
            self.photo = ImageTk.PhotoImage(self.im)

            if self.counter == 0:
                self.cv1.create_image(self.imwidth // 2, self.imheight // 2, image = self.photo)

            else:
                self.cv1.delete("all")
                self.cv1.create_image(self.imwidth // 2, self.imheight // 2, image = self.photo)

            
            # Truncate the image name to keep it short
            if len(img) > 18:
                if '/' in img:
                    img_name = '../' + img.split('/')[-1].split('.')[0]
                else:
                    img_name = '..' + img.split('.')[0][-16:]
            elif len(img) > 10:
                img_name = img.split('.')[0]
            else:
                img_name = img

            # Edit the text information
            self.infoText.config(state=tk.NORMAL)
            self.infoText.delete('1.0', '1.end')
            self.infoText.insert('1.0',"Image {}/{} - Filename: {}".format(self.counter+1,self.max_count+1,img_name), 'c')
            self.infoText.config(state=tk.DISABLED)

            # Reset all button styles (colors and outline)
            self.saveButton.config(highlightbackground = self.buttonOrigColor, bg = self.buttonBgOrigColor)
            self.masterButton.config(highlightbackground= self.buttonOrigColor, bg = self.buttonBgOrigColor)
            if self.catButton:
                for i in range(len(self.catButton)):
                    self.catButton[i].config(highlightbackground = self.buttonOrigColor, bg = self.buttonBgOrigColor)

            # Display the associated label(s) from any user as colored background for the label button
            ## If in reconcileMode, display the chosen label in grey
            if self.reconciledLabelsDict and img in self.reconciledLabelsDict:
                label = self.reconciledLabelsDict[img]
                idxLabel = self.categories.index(label)
                self.catButton[idxLabel].config(highlightbackground='#3E4149', bg = '#3E4149')
            else:
                labelDict = {}
                ## In normal mode, check allLabeledDict for other user's labels
                if img in self.allLabeledDict:
                    for (user, label) in self.allLabeledDict[img].items():
                        ### Current user's data might not be up to date in allLabeledDict, will user self.labeled
                        if user != self.username:
                            if label in labelDict:
                                labelDict[label].append(self.userColors[user])
                            else:
                                labelDict[label] = [self.userColors[user]]
                ## Get curent user's label from self.labeled
                if img in self.labeled:
                    label = self.labeled[img]
                    if label in labelDict and self.userColor not in labelDict[label]:
                        labelDict[label].append(self.userColor)
                    elif label not in labelDict:
                        labelDict[label] = [self.userColor]
                ## Finally, change the button color accordingly
                for label in labelDict:
                    idxLabel = self.categories.index(label)
                    if len(labelDict[label]) == 1:
                        self.catButton[idxLabel].config(highlightbackground=labelDict[label][0], bg = labelDict[label][0])
                    else:
                        self.catButton[idxLabel].config(highlightbackground='#3E4149', bg = '#3E4149')

            # Disable back button if on first image
            if self.counter == 0:
                self.prevButton.config(state = tk.DISABLED)
                self.firstButton.config(state = tk.DISABLED)
            else:
                self.prevButton.config(state = tk.NORMAL)
                self.firstButton.config(state = tk.NORMAL)

            # Disable next button on last image
            if self.counter == self.max_count:
                self.nextButton.config(state = tk.DISABLED)
                self.lastButton.config(state = tk.DISABLED)
            else:
                self.nextButton.config(state = tk.NORMAL)
                self.lastButton.config(state = tk.NORMAL)

            # Auto-save and auto-refresh
            if self.saveInterval != 0 and (time.time() - self.saveTimestamp) > self.saveInterval:
                logging.debug("display_image - Auto-save triggered")
                self.saveTimestamp = time.time()
                self.save()

    def responsiveCanvas(self, event):
        logging.debug("Redrawing frame1 following a size change event. New size: {}".format((event.width, event.height)))
        self.imwidth = event.width
        self.imheight = event.height
        self.display_image()

    ##############################
    ### Helper functions #########
    ##############################

    def add_label(self):
        '''Adds a label to the list of categories'''

        # Obtain new label name from user
        labelName = simpledialog.askstring("New label", "Label name:")

        # If the user cancels or doesn't enter anything, return
        if not labelName:
            return

        # Normalize the label name
        sanLabel = self.sanitize_label_name(labelName)

        # If the label already exists return without doing anything
        if sanLabel in self.categories:
            logging.warning("This label already exists")
            return

        # Add to category list
        self.categories.append(sanLabel)

        # Save labels to file
        if not self.labels_from_file:
            with open(self.labelpath,'wb') as f:
                pickle.dump(self.categories, f)

        # Redraw label buttons
        self.draw_label_buttons()

    def sanitize_label_name(self, rawString):
        '''Removes leading and trailing spaces, makes label lowercase and capitalize the first word'''
        return rawString.strip().lower().capitalize()

    def sanitize_user_name(self, rawString):
        '''Removes all spaces and makes lowercase'''
        return ''.join(rawString.strip().lower().split())
            
    def get_all_users(self):
        '''Returns a list of all users detected in the directory'''
        return [f.split('_')[1].split('.')[0] for f in os.listdir(self.folder) if (f.endswith('.pkl') and f.startswith('labeled_') and 'master' not in f)]
    
    def update_all_dict(self):
        '''Loads the labeling data from all detected users into a master dictionary.

        self.allLabeledDict: {picName: {user: label}}
        '''

        logging.debug("update_all_dict - Refreshing master dictionary")

        self.allLabeledDict = {}

        # If redundantMode is enabled, do not load other user's dictionaries
        if self.redundantMode:
            return

        for user in self.users:
            # Current user is treated separately because dict is already loaded and might not exist on disk
            if user == self.username:
                for (imageName, label) in self.labeled.items():
                    if imageName in self.allLabeledDict:
                        self.allLabeledDict[imageName][user] = label
                    else:
                        self.allLabeledDict[imageName] = {user: label}
            # For other users, load their dict and dump data into the allLabeledDict dictionary
            else:
                dictPath = self.folder + "/labeled_" + user +".pkl"
                userDict = self.load_dict(dictPath)
                for (imageName, label) in userDict.items():
                    if imageName in self.allLabeledDict:
                        self.allLabeledDict[imageName][user] = label
                    else:
                        self.allLabeledDict[imageName] = {user: label}

    def update_user_list(self):

        logging.debug("update_user_list - Refreshing user list")

        # Update the list of users
        newUsers = self.get_all_users()
        ## If new users are detected, update the names in the UI
        if newUsers != self.users:
            self.users = newUsers
            self.update_users_displayed()

    def refresh_all_dict(self):
        '''Updates the list of users and master dictionary then refreshes the img_list accordingly. Does not re-explore the directory.'''

        #Update the list of users
        self.update_user_list()
        
        # Update the master dict by refreshing it
        self.update_all_dict()

        # Rebuild the image_list
        labeledByCurrentUser = []
        labeledByOtherUser = []
        toLabel = []
        for img in self.image_list:
            if img in self.labeled:
                labeledByCurrentUser.append(img)
            elif img in self.allLabeledDict:
                labeledByOtherUser.append(img)
            else:
                toLabel.append(img)
        
        alreadyLabeled = labeledByOtherUser + labeledByCurrentUser
        self.counter = len(alreadyLabeled)
        self.image_list =  alreadyLabeled + toLabel

    def previous_image(self, *args):
        '''Displays the previous image'''
        if self.counter > 0:
            self.counter += -1
            self.display_image()
        else:
            logging.info("This is the first image, can't go back")
    
    def next_image(self, *args):
        '''Displays the next image'''
        if self.counter <= self.max_count:
            self.counter += 1
            self.display_image()
        else:
            logging.info("No more images")

    def goto_first_image(self, *args):
        '''Display the first image of the list'''
        self.counter = 0
        self.display_image()

    def goto_last_image(self, *args):
        '''Display the last image of the list'''
        self.counter = self.max_count
        self.display_image()

    def goto_next_unlabeled(self):
        '''Displays the unlabeled image with the smallest index number'''
        if self.reconcileMode:
            self.counter = len(self.sort_conflicting_imgs()[0])
        else:
            for idx, img in enumerate(self.image_list):
                if img not in self.labeled and img not in self.allLabeledDict:
                    self.counter = idx
                    break
        self.display_image()

    def sort_conflicting_imgs(self):
        '''Returns sub-lists of images: (labeledAgreed, labeledDisagreed, toLabel)'''

        labeledAgreed = []
        labeledDisagreed = []
        toLabel = []

        # Update master dict to have a common reference
        self.update_user_list()
        self.update_all_dict()
        
        for img in self.image_list:
            if img in self.allLabeledDict:
                labelList = self.allLabeledDict[img]
                # If only one user labeled the image, it is not disagreed
                if len(labelList) == 1:
                    labeledAgreed.append(img)
                # If multiple labels are found, compare the labels
                elif len(labelList) > 1:
                    selectedLabel = None
                    for (_, label) in labelList.items():
                        if not selectedLabel:
                            selectedLabel = label
                        elif label != selectedLabel:
                            labeledDisagreed.append(img)
                            break
                    if img not in labeledDisagreed:
                        labeledAgreed.append(img)
            else:
                toLabel.append(img)

        return (labeledAgreed, labeledDisagreed, toLabel)

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
            #elif e.char == 'd': # For debug only
            #    self.debug_prints()
            else:
                pass

    def debug_prints(self):
        print("----- allLabeledDict Dict entry -----")
        if self.image_list[self.counter] in self.allLabeledDict:
            print(self.allLabeledDict[self.image_list[self.counter]])
        else:
            print("Not found")
        print("----- reconciledLabelsDict entry -----")
        if self.reconciledLabelsDict and self.image_list[self.counter] in self.reconciledLabelsDict:
            print(self.reconciledLabelsDict[self.image_list[self.counter]])
        else:
            print("Not found")
        print("----- labeledDict entry -----")
        if self.image_list[self.counter] in self.labeled:
            print(self.labeled[self.image_list[self.counter]])
        else:
            print("Not found")

    def save(self):
        '''Save the labeled dictionary to disk'''

        if self.reconcileMode:
            # Load all user's dictionaries in memory
            userDicts = {}
            for user in self.users:
                userDicts[user] = self.load_dict(self.folder + "/labeled_" + user +".pkl")

            # For each image, save master label if it exists, otherwise, save user's original label or nothing.
            for img in self.reconciledLabelsDict:
                for (_, userDict) in userDicts.items():
                    userDict[img] = self.reconciledLabelsDict[img]
            
            for (user, userDict) in userDicts.items():
                self.dump_dict(userDict, self.folder + '/labeled_' + user + '.pkl')
            
            logging.info("Updated save data for users: {}".format(self.users))

        else:
            self.dump_dict(self.labeled, self.savepath)
            logging.info("Saved data to disk")

        self.saveButton.config(highlightbackground='#3E4149', bg = '#3E4149')
        self.saved = True
    
    def load_dict(self, file):
        '''Read a pickeled dictionary from file'''
        with open(file,"rb") as f:
            return pickle.load(f)
    
    def dump_dict(self, dict, file):
        '''Pickle a dictionary to file'''
        with open(file, 'wb') as f:
            pickle.dump(dict, f)

    def user_color_helper(self, username):
        '''Selects a color based on a username in a repeatable way also ensuring there are no conflicting colors if possible'''
        random.seed(a = username)
        color = random.choice(self.colors)
        while color in self.userColors.values() and (len(self.userColors) <= len(self.colors)):
            color = random.choice(self.colors)
        return color

    def exit(self):
        '''Cleanly exits the app'''
        logging.debug("Executing clean exit actions...")

        # Show the save dialog
        if not self.saved:
            result = askquestion('Save?', 'Do you want to save this session before leaving?', icon = 'warning')
            if result == 'yes':
                self.save()

        # Release the lock if the app obtained it
        if self.gotLock:
            self.lock.release()

        # Close the app cleanly
        self.quit()

    def errorClose(self):
        '''Closes the window when the app encouters an error it cannot recover from'''
        logging.debug("Executing error exit actions...")

        # Release the lock if the app obtained it
        if self.gotLock:
            self.lock.release()
    
        # Destroy the window and exit
        self.master.destroy()
        sys.exit()


class FsLock(object):
    '''
    A simple filesystem based lock mechanism to avoid multiple users logging in with the same username at once.
    '''
    def __init__(self, directory, username):
        self.filename = directory + '/.' + username + '_lock.txt'

        # If the lock file does not exist, create it now
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                f.write('unlocked')

    def acquire(self):
        if self.is_locked():
            raise Exception("Lock is already acquired.")     
        else:
            with open(self.filename, 'w') as f:
                f.write('locked')
            
    def release(self):
        with open(self.filename, 'w') as f:
            f.write('unlocked')

    def is_locked(self):
        with open(self.filename, 'r') as f:
            return f.read() == 'locked'

def delete_all_files(directory):
    '''Deletes all files created by simplabel in a directory, this resets the labels and all saved data'''

    save_files = [f for f in os.listdir(directory) if (f.endswith('.pkl') and f.startswith('label'))]
    save_files.extend([f for f in os.listdir(directory) if f.startswith('.') and f.endswith('_lock.txt')])
    if len(save_files) > 0:
        response = input("Are you sure you want to delete all saved files: {}? (y/n)".format(save_files))
        if response == 'y':
            for f in save_files:
                os.remove(os.path.join(directory,f))
            print("Successfully deleted all saved files")
        else:
            print("Cancelled deletion, your files are exactly where you left them ;)")
    else:
        print("No files found in {}".format(directory))
    return

def remove_label(directory, labelName):
    '''Removes a label from the label file after verifying it isn't in use'''

    labelToRemove = labelName.strip().lower().capitalize()

    # Load the label file to check the presence of the label to remove
    labelFile = directory + '/labels.pkl'
    if os.path.isfile(labelFile):
        with open(labelFile, 'rb') as f:
            labels = pickle.load(f)
        if labelToRemove not in labels:
            print("No such label in labels.pkl")
            return
    else:
        print("No label file found.")
        return
        
    
    # Get a list of users
    users = [f.split('_')[1].split('.')[0] for f in os.listdir(directory) if (f.endswith('.pkl') and f.startswith('labeled_'))]

    # Load each user's dictionary and check for the presense of the label to remove
    for user in users:
        dictPath = directory + "/labeled_" + user +".pkl"
        with open(dictPath, "rb") as f:
            userDict = pickle.load(f)
        if labelToRemove in userDict.values():
            print("Label {} is used by {}, cannot remove it from the list".format(labelToRemove, user))
            return

    # If the check have passed, remove the label from the list and resave the list
    labels.remove(labelToRemove)
    with open(labelFile, 'wb') as f:
        pickle.dump(labels, f)
    
    print("Successfully removed label {} from the list".format(labelToRemove))
    return

def main():

    #Setup parser
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--directory", default=None, help="Path of the directory")
    ap.add_argument("-l", "--labels", nargs='+', default=None, help="List of labels")
    ap.add_argument("-v", "--verbose", action='count', default=0, help="Enable verbose mode")
    ap.add_argument("-u", "--user", help="Set username for the current session")
    ap.add_argument("-r", "--redundant", action='store_true', help="Redundant mode: do not show other labeler's selections")
    ap.add_argument("--delete-all", action='store_true', help="Deletes all files created by simplabel in a directory, this resets the labels and all saved data")
    ap.add_argument("--reset-lock", action='store_true', help="Overrides the lock in case of incorrect lockout")
    ap.add_argument("--remove-label", help="Remove a label from the list")

    args = ap.parse_args()

    # Get the variables from parser
    rawDirectory = args.directory
    categories = args.labels
    verbosity = args.verbose
    username = args.user
    bResetLock = args.reset_lock
    bRedundant = args.redundant

    # Reset all saved data if requested
    if args.delete_all:
        delete_all_files(rawDirectory)
        sys.exit(0)

    # Remove label
    if args.remove_label:
        if not rawDirectory:
            print("No directory specified. You must pass the directory containing the label file with -d")
        remove_label(rawDirectory, args.remove_label)
        sys.exit(0)

    # Launch the app
    root = tk.Tk() 
    MyApp = ImageClassifier(root, directory = rawDirectory, categories = categories, verbose = verbosity, username = username, bResetLock = bResetLock, bRedundant = bRedundant)
    tk.mainloop()