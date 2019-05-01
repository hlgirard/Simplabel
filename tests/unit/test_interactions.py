import unittest
from unittest.mock import patch

import os
import pickle
import tkinter
import _tkinter

from simplabel import ImageClassifier

class TestLabelingTool(unittest.TestCase):

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.label_file = os.path.join(self.test_folder, 'labels.pkl')

        self.cleanup_files()

        # Create label file
        labels = ["Label1", "Label2"]
        with open(self.label_file, 'wb') as f:
            pickle.dump(labels, f)

        self.root=tkinter.Tk()
        self.pump_events()
        self.classifier = ImageClassifier(self.root, directory=self.test_folder, username="testuser")

    def tearDown(self):
        if self.classifier.gotLock:
            self.classifier.lock.release()
        if self.root:
            self.root.destroy()
            self.pump_events()

        self.cleanup_files()

    def pump_events(self):
        while self.root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass

    def cleanup_files(self):
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

        # Delete label file
        if os.path.exists(self.label_file):
            os.remove(self.label_file)

    def test_next_image_button(self):
        prevValue = self.classifier.counter
        self.classifier.nextButton.invoke()
        self.assertEqual(self.classifier.counter, prevValue + 1)

    def test_previous_image_button(self):
        while self.classifier.counter == 0:
            self.classifier.next_image()
        prevValue = self.classifier.counter
        self.classifier.prevButton.invoke()
        self.assertEqual(self.classifier.counter, prevValue - 1)

    def test_goto_last_image_button(self):
        self.classifier.lastButton.invoke()
        self.assertEqual(self.classifier.counter, len(self.classifier.image_list) - 1)

    def test_label_one_image(self):
        '''Checks that clicking on a label button advances to the next image and has labeled the previous image'''
        prevValue = self.classifier.counter
        imgName = self.classifier.image_list[prevValue]
        self.classifier.catButton[0].invoke()
        if prevValue < len(self.classifier.image_list) - 1:
            self.assertEqual(self.classifier.counter, prevValue + 1)
        else:
            self.assertEqual(self.classifier.counter, prevValue)
        self.assertEqual(self.classifier.labeled[imgName], "Label1")

    def test_labeled_image_has_colored_button(self):
        '''Checks that a labeled image has a colored label button with the user's color'''
        self.classifier.catButton[1].invoke()
        self.classifier.firstButton.invoke()

        # Check that the Label2 button has the color of the user
        self.assertEqual(self.classifier.catButton[1].config()['highlightbackground'][-1], self.classifier.userColor)
        self.assertEqual(self.classifier.catButton[1].config()['background'][-1], self.classifier.userColor)

        # Check that the Label1 button has the original color
        self.assertEqual(self.classifier.catButton[0].config()['highlightbackground'][-1], self.classifier.buttonOrigColor)
        self.assertEqual(self.classifier.catButton[0].config()['background'][-1], self.classifier.buttonBgOrigColor)
        
    def test_save_labels(self):
        '''Checks that the labels are correctly saved to file'''
        imgName = self.classifier.image_list[self.classifier.counter]
        self.classifier.catButton[1].invoke()
        self.classifier.saveButton.invoke()

        with open(os.path.join(self.test_folder, "labeled_testuser.pkl"), 'rb') as savefile:
            savedict = pickle.load(savefile)

        self.assertEqual(savedict[imgName], self.classifier.labeled[imgName])

    def test_goto_last_unlabeled_image(self):
        self.classifier.catButton[0].invoke()
        self.classifier.firstButton.invoke()
        self.assertEqual(self.classifier.counter, 0)
        self.classifier.nextUnlabeledButton.invoke()
        self.assertEqual(self.classifier.counter, 1)

    @patch('simplabel.simpledialog.askstring')
    def test_add_label(self, mock_dialog):
        '''Check that adding a label through the GUI adds it to the list, creates a new button and saves it to file'''

        # Mock the dialog that requests the name of the label
        mock_dialog.configure_mock(return_value="Label3")

        # Add a label
        self.classifier.addCatButton.invoke()

        # Check that the label was added to the list
        self.assertEqual(self.classifier.categories[2], "Label3")

        # Check that a button was created for it
        self.assertEqual(len(self.classifier.catButton), 3)

        # Check that the label was saved to file
        with open(self.label_file, 'rb') as f:
            savedlabels = pickle.load(f)

        self.assertIn("Label3", savedlabels)

    @patch('simplabel.simpledialog.askstring')
    def test_add_already_existing_label(self, mock_dialog):
        '''Check that adding an already existing label through the GUI does not add it to the list'''

        # Mock the dialog that requests the name of the label
        mock_dialog.configure_mock(return_value="Label1")

        # Add a label
        self.classifier.addCatButton.invoke()

        # Check that the label was not added to the list
        self.assertEqual(len(self.classifier.categories), 2)

        # Check that a button was not created for it
        self.assertEqual(len(self.classifier.catButton), 2)

        # Check that the label was saved to file
        with open(self.label_file, 'rb') as f:
            savedlabels = pickle.load(f)

        self.assertEqual(len(savedlabels),2)

    @patch('simplabel.simpledialog.askstring')
    def test_add_10_labels(self, mock_dialog):
        '''Check that adding 10 labels works as intended (3 rows of labels)'''

        # Add labels
        mock_dialog.configure_mock(return_value="Label3")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label4")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label5")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label6")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label7")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label8")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label9")
        self.classifier.addCatButton.invoke()
        mock_dialog.configure_mock(return_value="Label10")
        self.classifier.addCatButton.invoke()

        # Check that the labels were added to the list
        self.assertEqual(len(self.classifier.categories), 10)

        # Check that a button werecreated
        self.assertEqual(len(self.classifier.catButton), 10)

        # Check that there are 3 rows
        self.assertEqual(len(self.classifier.labelFrameList), 3)

        # Check that the labels were saved to file
        with open(self.label_file, 'rb') as f:
            savedlabels = pickle.load(f)

        self.assertEqual(len(savedlabels),10)
    
    
if __name__ == '__main__':
    unittest.main()