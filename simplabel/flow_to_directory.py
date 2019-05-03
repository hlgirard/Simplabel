import argparse
import os
import pickle
import shutil
import sys
import tkinter as tk

def flow_to_dict(rawDirectory, labelledDirectory=None):
    '''
    Copies labelled images to discting directories by label

    Arguments
    --------
    rawDirectory: string
        Path to the directory containing raw images. It must also contain a labeled.pkl file created with simplabel containing the labels
    labelledDirectory: string
        Path to the output directory. A folder will be created for each label in the dictionary.
    '''

    # Detected users
    users = [f.split('_')[1].split('.')[0] for f in os.listdir(rawDirectory) if (f.endswith('.pkl') and f.startswith('labeled_'))]

    if not users:
        print("No label files found in directory.")
        sys.exit()

    # Open the labelled dictionary
    if 'master' in users:
        dictPath = rawDirectory + '/labeled_master.pkl'
    else:
        username = input("Enter username to flow {}:".format(users))
        dictPath = rawDirectory + '/labeled_{}.pkl'.format(username)
    
    if os.path.exists(dictPath):
        with open(dictPath,'rb') as f:
            labelled_dict = pickle.load(f)
    else:
        print("No dictionary found at: {}".format(dictPath))
        sys.exit()
        
    # Get all categories that exist in the dictionary
    categories = set(labelled_dict.values())
    # If no output directory is passed, use the input directory
    if not labelledDirectory:
        labelledDirectory = rawDirectory
    # Check existence of output directory
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


def main():
    #Setup parser
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input-directory", default=os.getcwd(), help="Path of the directory containing the raw images and labeled.pkl file. Defaults to current directory")
    ap.add_argument("-o", "--output-directory", help="Path of the output directory, will be created if it does not exist")

    args = ap.parse_args()

    # Get the variables from parser
    rawDirectory = args.input_directory
    outDirectory = args.output_directory

    flow_to_dict(rawDirectory, outDirectory)
    