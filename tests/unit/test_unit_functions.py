import unittest
from unittest.mock import patch

from io import StringIO
import os
import json
import tkinter
import _tkinter

from simplabel import ImageClassifier, remove_label, delete_all_files

class Test_Unit_Functions(unittest.TestCase):

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.label_file = os.path.join(self.test_folder, '.labels.json')

        self.cleanup_files()

        # Create label file
        labels = ["Label1", "Label2"]
        with open(self.label_file, 'w') as f:
            json.dump(labels, f)

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

    def test_delete_all_files(self):
        with patch('builtins.input', return_value='y'):
            delete_all_files(self.test_folder)

        savefiles = [file for file in os.listdir(self.test_folder) if file.startswith("labeled_") and file.endswith(".json")]
        lockfiles = [file for file in os.listdir(self.test_folder) if file.endswith("_lock.txt")]
        
        self.assertEqual(len(savefiles), 0)
        self.assertEqual(len(lockfiles), 0)
        self.assertFalse(os.path.exists(self.label_file))

class Test_Remove_Labels(unittest.TestCase):

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.label_file = os.path.join(self.test_folder, '.labels.json')

        self.cleanup_files()

        # Create label file
        labels = ["Label1", "Label2"]
        with open(self.label_file, 'w') as f:
            json.dump(labels, f)

        self.root=tkinter.Tk()
        self.pump_events()
        self.classifier = ImageClassifier(self.root, directory=self.test_folder, username="testuser")

    def tearDown(self):
        self.cleanup_files()

    def pump_events(self):
        while self.root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
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

    def test_remove_unused_label(self):
        '''Removing an unused label should work'''
        # Classify an image with Label1
        self.classifier.catButton[0].invoke()
        self.classifier.save()

        # Close the app
        if self.classifier.gotLock:
            self.classifier.lock.release()
        if self.root:
            self.root.destroy()
            self.pump_events()

        with patch('sys.stdout', new=StringIO()) as fake_out:
            remove_label(self.test_folder, "Label2")
            printed = fake_out.getvalue().strip()

        self.assertEqual(printed, "Successfully removed label Label2 from the list".strip())
        
        with open(self.label_file, 'r') as f:
            labels = json.load(f)
        
        self.assertNotIn("Label2", labels)

    def test_remove_used_label(self):
        '''Removing a used label should fail and the label should remain in labels.json'''

        # Classify an image with Label1
        self.classifier.catButton[0].invoke()
        self.classifier.save()

        # Close the app
        if self.classifier.gotLock:
            self.classifier.lock.release()
        if self.root:
            self.root.destroy()
            self.pump_events()

        with patch('sys.stdout', new=StringIO()) as fake_out:
            remove_label(self.test_folder, "Label1")
            printed = fake_out.getvalue().strip()

        self.assertEqual(printed, "Label Label1 is used by testuser, cannot remove it from the list".strip())
        
        with open(self.label_file, 'r') as f:
            labels = json.load(f)
        
        self.assertIn("Label1", labels)

    def test_remove_label_when_no_label_file(self):
        '''Should print an error message'''

        # Close the app
        if self.classifier.gotLock:
            self.classifier.lock.release()
        if self.root:
            self.root.destroy()
            self.pump_events()

        self.cleanup_files()

        with patch('sys.stdout', new=StringIO()) as fake_out:
            remove_label(self.test_folder, "Label1")
            printed = fake_out.getvalue().strip()

        self.assertEqual(printed, "No label file found.".strip())





class Test_Misformed_Labels(unittest.TestCase):
    '''Test that the app is robust to misformed labels in the labels.json file'''

    def setUp(self):

        self.test_folder = 'tests/test_images'
        self.label_file = os.path.join(self.test_folder, '.labels.json')

        self.cleanup_files()

        # Create label file
        labels = ["Label1", "label2", "Label1", "label with spaces", "trailing space ", " leading space"]
        with open(self.label_file, 'w') as f:
            json.dump(labels, f)

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

    def test_labels_sanitized(self):
        self.assertIn("Label2", self.classifier.categories)
        self.assertIn("Label with spaces", self.classifier.categories)
        self.assertIn("Trailing space", self.classifier.categories)
        self.assertIn("Leading space", self.classifier.categories)

    def test_duplicates_removes(self):
        expectedLabelList = ["Label1", "Label2", "Label with spaces", "Trailing space", "Leading space"]
        self.assertEqual(expectedLabelList, self.classifier.categories)