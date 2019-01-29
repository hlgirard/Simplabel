import os
import pickle
import shutil

def move_to_dict(rawDirectory, labelledDirectory, labelled_dict):
    # Get all categories that exist in the dictionary
    categories = set(labelled_dict.values())
    # Check existence of main directory
    if not os.path.exists(labelledDirectory):
        os.mkdir(labelledDirectory)
    # Check existence of sub folders, create if necessary
    for label in categories:
        labelDirect = labelledDirectory + '/' + label
        if not os.path.exists(labelDirect):
            os.mkdir(labelDirect)
    # For each file in dictionary, move it to corresponding directory
    for image, label in labelled_dict.items():
        labelDirect = labelledDirectory + '/' + label
        print("Copying {} to {}".format(image, labelDirect))
        shutil.copy2(rawDirectory + '/' + image, labelDirect)



if __name__ == "__main__":
    rawDirectory = 'data/raw'
    labelledDirectory = 'data/labelled'
    dictPath = rawDirectory + '/labelled.pkl'

    with open(dictPath,'rb') as f:
        labelled_dict = pickle.load(f)

    move_to_dict(rawDirectory, labelledDirectory, labelled_dict)