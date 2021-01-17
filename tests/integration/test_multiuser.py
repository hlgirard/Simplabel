import unittest

import os
import json
import tkinter
import _tkinter

from simplabel import ImageClassifier

class TestMultiUser(unittest.TestCase):

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.label_file = os.path.join(self.test_folder, '.labels.json')

        self.cleanup_files()

        # Create label file
        labels = ['Label1', 'Label2']
        with open(self.label_file, 'w') as f:
            json.dump(labels, f)

        # User 1
        self.root1 = tkinter.Tk()
        self.pump_events(self.root1)
        self.classifier1 = ImageClassifier(self.root1, directory=self.test_folder, username="testuser1")

    def tearDown(self):
        self.cleanup_files()
        
    def pump_events(self, root):
        while root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass

    def cleanup_files(self):
        # Delete any saved files
        savefiles = [file for file in os.listdir(self.test_folder) if file.startswith("labeled_") and file.endswith(".json")]
        if savefiles:
            for file in savefiles:
                os.remove(os.path.join(self.test_folder, file))

        # Delete all lock files
        lockfiles = [file for file in os.listdir(self.test_folder) if file.endswith("_lock.txt")]
        if lockfiles:
            for file in lockfiles:
                os.remove(os.path.join(self.test_folder, file))

        # Delete label file
        if os.path.exists(self.label_file):
            os.remove(self.label_file)


    def test_detect_other_user(self):
        '''User 1 opens the app, saves a label. User 2 opens the app, detects User 1's saved data'''
        
        imgName = self.classifier1.image_list[self.classifier1.counter]
        self.classifier1.catButton[0].invoke()
        self.classifier1.saveButton.invoke()

        # User 1 closes the window
        if self.classifier1.gotLock:
            self.classifier1.lock.release()
        if self.root1:
            self.root1.destroy()
            self.pump_events(self.root1)

        # User 2 opens a new window
        root2 = tkinter.Tk()
        self.pump_events(root2)
        classifier2 = ImageClassifier(root2, directory=self.test_folder, username="testuser2")

        # Check that user1 is detected
        self.assertIn("testuser1", classifier2.users)

        # Check that user1's label is detected
        self.assertIn(imgName, classifier2.allLabeledDict)

        # Check that the initial counter is 1 (image 0 is already labeled)
        self.assertEqual(classifier2.counter, 1)

        # Check that the first image in the list is the one labeled by user 1
        self.assertEqual(classifier2.image_list[0], imgName)

        # Check that the color of user1 is displayed on the button corresponding to the label
        classifier2.firstButton.invoke() # Go to the first image (labeled by user1)
        self.assertEqual(classifier2.catButton[0].config()['highlightbackground'][-1], classifier2.userColors["testuser1"])
        self.assertEqual(classifier2.catButton[0].config()['background'][-1], classifier2.userColors["testuser1"])

        # Check that an image labeled by both users shows as dark grey
        classifier2.catButton[0].invoke() # Label this image with user2 as well
        classifier2.firstButton.invoke()
        self.assertEqual(classifier2.catButton[0].config()['highlightbackground'][-1], '#3E4149')
        self.assertEqual(classifier2.catButton[0].config()['background'][-1], '#3E4149')

        # User 2 closes the window
        if classifier2.gotLock:
            classifier2.lock.release()
        if root2:
            root2.destroy()
            self.pump_events(root2)

    def test_reconcile_and_make_master(self):
        '''
        User1 opens the app, labels all images. User 2 opens the app, labels all images.
        User2 enters reconcile mode, reconciles the labels and saves.
        User2 makes master label file
        '''

        # User1 labels all images as Label1 and saves
        self.classifier1.catButton[0].invoke()
        self.classifier1.catButton[0].invoke()
        self.classifier1.catButton[0].invoke()
        self.classifier1.saveButton.invoke()

        # User 1 closes the window
        if self.classifier1.gotLock:
            self.classifier1.lock.release()
        if self.root1:
            self.root1.destroy()
            self.pump_events(self.root1)

        # User 2 opens the app
        root2 = tkinter.Tk()
        self.pump_events(root2)
        classifier2 = ImageClassifier(root2, directory=self.test_folder, username="testuser2")

        # Check that the app opens on the last image (all images are labeled at this point)
        self.assertEqual(classifier2.counter, len(classifier2.image_list) - 1)

        # User 2 goes to first image and labels one as Label1 and one as Label 2
        classifier2.firstButton.invoke()
        classifier2.catButton[0].invoke()
        classifier2.catButton[1].invoke()

        # Check that the first image has agreed labels (grey coloring)
        classifier2.firstButton.invoke()
        self.assertEqual(classifier2.catButton[0].config()['highlightbackground'][-1], '#3E4149')
        self.assertEqual(classifier2.catButton[0].config()['background'][-1], '#3E4149')

        self.assertEqual(classifier2.catButton[1].config()['highlightbackground'][-1], classifier2.buttonOrigColor)
        self.assertEqual(classifier2.catButton[1].config()['background'][-1], classifier2.buttonBgOrigColor)

        self.assertEqual(classifier2.labeled[classifier2.image_list[classifier2.counter]], "Label1")
        self.assertEqual(classifier2.allLabeledDict[classifier2.image_list[classifier2.counter]], {"testuser1": "Label1"})

        # Check that the second image labels disagree
        classifier2.nextButton.invoke()
        self.assertEqual(classifier2.catButton[0].config()['highlightbackground'][-1], classifier2.userColors["testuser1"])
        self.assertEqual(classifier2.catButton[0].config()['background'][-1], classifier2.userColors["testuser1"])

        self.assertEqual(classifier2.catButton[1].config()['highlightbackground'][-1], classifier2.userColor)
        self.assertEqual(classifier2.catButton[1].config()['background'][-1], classifier2.userColor)

        self.assertEqual(classifier2.labeled[classifier2.image_list[classifier2.counter]], "Label2")
        self.assertEqual(classifier2.allLabeledDict[classifier2.image_list[classifier2.counter]], {"testuser1": "Label1"})

        # Save and Enter reconcile mode
        classifier2.saveButton.invoke()
        classifier2.reconcileButton.invoke()

        # Check that the counter is 2 (two agreed | one disagreed)
        self.assertEqual(classifier2.counter, 2)

        # Agree with User1 on the only disagreed image, save and exit reconcile mode
        classifier2.catButton[0].invoke()
        classifier2.saveButton.invoke()
        classifier2.reconcileButton.invoke()

        # Make master
        classifier2.masterButton.invoke()

        # Check contents of the master_labeled.json
        with open(os.path.join(self.test_folder, "labeled_master.json"), 'r') as savefile:
            savedict = json.load(savefile)

        testdict = {"all_crystals.JPG": "Label1", "empty_droplets.JPG": "Label1", "some_crystals.JPG": "Label1"}
        self.assertEqual(savedict, testdict)

        # User 2 closes the window
        if classifier2.gotLock:
            classifier2.lock.release()
        if root2:
            root2.destroy()
            self.pump_events(root2)

    def test_redundant_mode(self):
        '''
        User1 opens the app, labels all images. User2 opens the app in redundant mode.
        User2 should start from the begining and not see User1's labels.
        '''

        # User1 labels all images as Label1 and saves
        self.classifier1.catButton[0].invoke()
        self.classifier1.catButton[1].invoke()
        self.classifier1.catButton[0].invoke()
        self.classifier1.saveButton.invoke()

        # User 1 closes the window
        if self.classifier1.gotLock:
            self.classifier1.lock.release()
        if self.root1:
            self.root1.destroy()
            self.pump_events(self.root1)

        # User 2 opens the app
        root2 = tkinter.Tk()
        self.pump_events(root2)
        classifier2 = ImageClassifier(root2, directory=self.test_folder, username="testuser2", bRedundant=True)

        # Check that the app opens on the first image
        self.assertEqual(classifier2.counter, 0)

        # User 2 labels all the images (same labels as label 1)
        classifier2.firstButton.invoke()
        classifier2.catButton[0].invoke()
        classifier2.catButton[0].invoke()
        classifier2.catButton[0].invoke()

        # Check that the first image has the color of user2
        classifier2.firstButton.invoke()
        self.assertEqual(classifier2.catButton[0].config()['highlightbackground'][-1], classifier2.userColor)
        self.assertEqual(classifier2.catButton[0].config()['background'][-1], classifier2.userColor)

        self.assertEqual(classifier2.catButton[1].config()['highlightbackground'][-1], classifier2.buttonOrigColor)
        self.assertEqual(classifier2.catButton[1].config()['background'][-1], classifier2.buttonBgOrigColor)

        self.assertEqual(classifier2.labeled[classifier2.image_list[classifier2.counter]], "Label1")

        # Check that the second image has the color of user2
        classifier2.nextButton.invoke()
        self.assertEqual(classifier2.catButton[1].config()['highlightbackground'][-1], classifier2.buttonOrigColor)
        self.assertEqual(classifier2.catButton[1].config()['background'][-1], classifier2.buttonBgOrigColor)

        self.assertEqual(classifier2.catButton[0].config()['highlightbackground'][-1], classifier2.userColor)
        self.assertEqual(classifier2.catButton[0].config()['background'][-1], classifier2.userColor)

        self.assertEqual(classifier2.labeled[classifier2.image_list[classifier2.counter]], "Label1")

        # User 2 closes the window
        if classifier2.gotLock:
            classifier2.lock.release()
        if root2:
            root2.destroy()
            self.pump_events(root2)
        

