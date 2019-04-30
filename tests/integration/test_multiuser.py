import unittest

import os
import pickle
import tkinter
import _tkinter

from simplabel import ImageClassifier

class TestMultiUser(unittest.TestCase):

    def setUp(self):

        self.test_folder = 'tests/test_images'

        # User 1
        self.root1 = tkinter.Tk()
        self.pump_events(self.root1)
        self.classifier1 = ImageClassifier(self.root1, directory=self.test_folder, username="testuser1")
        
        # Delete any saved files
        savefiles = [file for file in os.listdir(self.test_folder) if file.startswith("labeled_") and file.endswith(".pkl")]
        if savefiles:
            for file in savefiles:
                os.remove(os.path.join(self.test_folder, file))

    def tearDown(self):
        # Delete any saved files
        savefiles = [file for file in os.listdir(self.test_folder) if file.startswith("labeled_") and file.endswith(".pkl")]
        if savefiles:
            for file in savefiles:
                os.remove(os.path.join(self.test_folder, file))

        # Delete all lock files
        lockfiles = [file for file in os.listdir(self.test_folder) if file.endswith("_lock.txt")]
        if lockfiles:
            for file in lockfiles:
                os.remove(os.path.join(self.test_folder, file))


    def pump_events(self, root):
        while root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass

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
        self.root2 = tkinter.Tk()
        self.pump_events(self.root2)
        self.classifier2 = ImageClassifier(self.root2, directory=self.test_folder, username="testuser2")

        # Check that user1 is detected
        self.assertIn("testuser1", self.classifier2.users)

        # Check that user1's label is detected
        self.assertIn(imgName, self.classifier2.allLabeledDict)

        # Check that the initial counter is 1 (image 0 is already labeled)
        self.assertEqual(self.classifier2.counter, 1)

        # Check that the first image in the list is the one labeled by user 1
        self.assertEqual(self.classifier2.image_list[0], imgName)

        # Check that the color of user1 is displayed on the button corresponding to the label
        self.classifier2.firstButton.invoke() # Go to the first image (labeled by user1)
        self.assertEqual(self.classifier2.catButton[0].config()['highlightbackground'][-1], self.classifier2.userColors["testuser1"])
        self.assertEqual(self.classifier2.catButton[0].config()['background'][-1], self.classifier2.userColors["testuser1"])

        # Check that an image labeled by both users shows as dark grey
        self.classifier2.catButton[0].invoke() # Label this image with user2 as well
        self.classifier2.firstButton.invoke()
        self.assertEqual(self.classifier2.catButton[0].config()['highlightbackground'][-1], '#3E4149')
        self.assertEqual(self.classifier2.catButton[0].config()['background'][-1], '#3E4149')

        # User 2 closes the window
        if self.classifier2.gotLock:
            self.classifier2.lock.release()
        if self.root2:
            self.root2.destroy()
            self.pump_events(self.root1)

