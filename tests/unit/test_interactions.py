import unittest

import os
import tkinter
import _tkinter

from simplabel import ImageClassifier

class TestLabelingTool(unittest.TestCase):

    def setUp(self):
        self.root=tkinter.Tk()
        self.pump_events()
        self.test_folder = 'tests/test_images'
        self.classifier = ImageClassifier(self.root, directory=self.test_folder)

    def tearDown(self):
        if self.classifier.gotLock:
            self.classifier.lock.release()
        if self.root:
            self.root.destroy()
            self.pump_events()

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

    




if __name__ == '__main__':
    unittest.main()