# Simplabel

Graphical tool to manually label images in disctinct categories to build training datasets.
Simply pass a list of categories, a directory containing images and start labelling.
Supports keyboard bindings to label even faster!

![screenshot](docs/screenshot_190124.png)

## Installation

Clone the repository to your computer

```
git clone https://github.com/hlgirard/Simplabel.git
```

and instal with pip 

```
cd Simplabel
pip install .
```

## Usage

### Command line tool

Pass the categories and image directory on the command line to start the GUI

```
simplabel --categories dog cat bird --directory path/to/image/directory
```

### Python object

```python
import simplabel

root = tk.Tk() 
directory = "data/raw"
categories = ['dog', 'cat', 'bird']
MyApp = ImageClassifier(root, directory, categories)
tk.mainloop()
```

### Saved labels

The app saves a labeled.pkl file that contains a pickeled dictionary {image_name.jpg: label}. To import the dictionary, use the following sample code:

```python
import pickle

with open(file,"rb") as f:
    label_dict = pickle.load(f)
```

### Graphical interface

Use the on-screen buttons to select a label for the current image and advance to the next one. Number keys correspond to labels and can be used instead.
