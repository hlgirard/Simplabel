import unittest

import os
import pickle
import tkinter
import _tkinter

from simplabel import ImageClassifier

class TestLabelingTool(unittest.TestCase):

    def setUp(self):
        self.root=tkinter.Tk()
        self.pump_events()
        self.test_folder = 'tests/test_images'
        self.classifier = ImageClassifier(self.root, directory=self.test_folder, username="testuser")

    def tearDown(self):
        if self.classifier.gotLock:
            self.classifier.lock.release()
        if self.root:
            self.root.destroy()
            self.pump_events()

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

    def pump_events(self):
        while self.root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass

    def test_loads_all_images(self):
        self.assertEqual(len(self.classifier.image_list), 3)

    def test_next_image(self):
        prevValue = self.classifier.counter
        self.classifier.next_image()
        self.assertEqual(self.classifier.counter, prevValue + 1)

    def test_next_image_button(self):
        prevValue = self.classifier.counter
        self.classifier.nextButton.invoke()
        self.assertEqual(self.classifier.counter, prevValue + 1)

    def test_previous_image(self):
        while self.classifier.counter == 0:
            self.classifier.next_image()
        prevValue = self.classifier.counter
        self.classifier.previous_image()
        self.assertEqual(self.classifier.counter, prevValue - 1)

    def test_previous_image_button(self):
        while self.classifier.counter == 0:
            self.classifier.next_image()
        prevValue = self.classifier.counter
        self.classifier.prevButton.invoke()
        self.assertEqual(self.classifier.counter, prevValue - 1)

    def test_previous_image_on_first_image_remains(self):
        self.classifier.previous_image()
        self.assertEqual(self.classifier.counter, 0)

    def test_goto_last_image(self):
        self.classifier.goto_last_image()
        self.assertEqual(self.classifier.counter, len(self.classifier.image_list) - 1)

    def test_goto_last_image_button(self):
        self.classifier.lastButton.invoke()
        self.assertEqual(self.classifier.counter, len(self.classifier.image_list) - 1)

    def test_lock_locked(self):
        self.assertTrue(self.classifier.lock.is_locked)

    def test_load_labels(self):
        self.assertEqual(self.classifier.categories, ["Label1", "Label2"])

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
    




if __name__ == '__main__':
    unittest.main()