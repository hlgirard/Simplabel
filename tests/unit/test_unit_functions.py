import unittest
from unittest.mock import patch

import os
import pickle
import tkinter
import _tkinter

from simplabel import ImageClassifier

class Test_Unit_Functions(unittest.TestCase):

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

    def test_loads_all_images(self):
        self.assertEqual(len(self.classifier.image_list), 3)

    def test_next_image(self):
        prevValue = self.classifier.counter
        self.classifier.next_image()
        self.assertEqual(self.classifier.counter, prevValue + 1)

    def test_previous_image(self):
        while self.classifier.counter == 0:
            self.classifier.next_image()
        prevValue = self.classifier.counter
        self.classifier.previous_image()
        self.assertEqual(self.classifier.counter, prevValue - 1)
    
    def test_previous_image_on_first_image_remains(self):
        self.classifier.previous_image()
        self.assertEqual(self.classifier.counter, 0)

    def test_goto_last_image(self):
        self.classifier.goto_last_image()
        self.assertEqual(self.classifier.counter, len(self.classifier.image_list) - 1)

    def test_next_on_last_image_remains(self):
        self.classifier.goto_last_image()
        prevValue = self.classifier.counter
        self.classifier.next_image()
        self.assertEqual(self.classifier.counter, prevValue)

    def test_lock_locked(self):
        self.assertTrue(self.classifier.lock.is_locked)

    def test_load_labels(self):
        self.assertEqual(self.classifier.categories, ["Label1", "Label2"])

    def test_got_username(self):
        self.assertEqual(self.classifier.username, 'testuser')

    def test_sanitize_label_inputs(self):
        self.assertEqual(self.classifier.sanitize_label_name(' Label'), 'Label')
        self.assertEqual(self.classifier.sanitize_label_name('Label '), 'Label')
        self.assertEqual(self.classifier.sanitize_label_name('label'), 'Label')
        self.assertEqual(self.classifier.sanitize_label_name(' Lab el '), 'Lab el')
    
    def test_sanitize_user_name(self):
        self.assertEqual(self.classifier.sanitize_user_name('userName'), 'username')
        self.assertEqual(self.classifier.sanitize_user_name(' user Name '), 'username')
        self.assertEqual(self.classifier.sanitize_user_name('UserName'), 'username')


class Test_Misformed_Labels(unittest.TestCase):
    '''Test that the app is robust to misformed labels in the labels.pkl file'''

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.label_file = os.path.join(self.test_folder, 'labels.pkl')

        self.cleanup_files()

        # Create label file
        labels = ["Label1", "label2", "Label1", "label with spaces", "trailing space ", " leading space"]
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

    def test_labels_sanitized(self):
        self.assertIn("Label2", self.classifier.categories)
        self.assertIn("Label with spaces", self.classifier.categories)
        self.assertIn("Trailing space", self.classifier.categories)
        self.assertIn("Leading space", self.classifier.categories)

    def test_duplicates_removes(self):
        expectedLabelList = ["Label1", "Label2", "Label with spaces", "Trailing space", "Leading space"]
        self.assertEqual(expectedLabelList, self.classifier.categories)
        