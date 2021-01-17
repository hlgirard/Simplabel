import unittest

import os
import json
import shutil
import tkinter
import _tkinter

from simplabel import ImageClassifier
from simplabel.flow_to_directory import flow_to_dict

class TestFlowToDict(unittest.TestCase):

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.labeled_dir = os.path.join(self.test_folder, 'labeledDir')
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

        # Delete labeled images flowed
        if os.path.exists(self.labeled_dir):
            shutil.rmtree(self.labeled_dir)

    def test_flow_to_dict_from_master(self):
        ''' User 1 labels images, makes master dictionary, closes the app. Flow_to_directory is then called'''

        file_names = []

        # User 1 labels images, two with Label1 and one with Label2
        file_names.append(self.classifier1.image_list[self.classifier1.counter])
        self.classifier1.catButton[0].invoke()
        file_names.append(self.classifier1.image_list[self.classifier1.counter])
        self.classifier1.catButton[0].invoke()
        file_names.append(self.classifier1.image_list[self.classifier1.counter])
        self.classifier1.catButton[1].invoke()
        self.classifier1.saveButton.invoke()
        self.classifier1.masterButton.invoke()

        # User 1 closes the window
        if self.classifier1.gotLock:
            self.classifier1.lock.release()
        if self.root1:
            self.root1.destroy()
            self.pump_events(self.root1)

        # Invoke flow to directory
        flow_to_dict(self.test_folder, self.labeled_dir)

        # Check that directories where created
        self.assertTrue(os.path.isdir(self.labeled_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.labeled_dir, 'Label1')))
        self.assertTrue(os.path.isdir(os.path.join(self.labeled_dir, 'Label2')))

        # Check that the correct number of file is in each directory
        self.assertEqual(len(os.listdir(os.path.join(self.labeled_dir, 'Label1'))), 2)
        self.assertEqual(len(os.listdir(os.path.join(self.labeled_dir, 'Label2'))), 1)

        # Check that the right files where moved to the right directory
        self.assertTrue(os.path.isfile(os.path.join(self.labeled_dir, 'Label1', file_names[0])))
        self.assertTrue(os.path.isfile(os.path.join(self.labeled_dir, 'Label1', file_names[1])))
        self.assertTrue(os.path.isfile(os.path.join(self.labeled_dir, 'Label2', file_names[2])))



