from ij import IJ, ImageStack, ImagePlus
from ij.io import FileSaver, OpenDialog
from ij.plugin import HyperStackConverter
from ij.gui import GenericDialog

import os

# Open dialog for user to select an image
od = OpenDialog("Choose an image", None)
img_path = od.getPath()

if img_path is None:
    raise RuntimeError("User did not choose a file.")

# Load image
imp = IJ.openImage(img_path)

# Retrieve image dimensions
channels = imp.getNChannels()
slices = imp.getNSlices()
frames = imp.getNFrames()

# Create new stacks for both channels
newStack1 = ImageStack(imp.width, imp.height)
newStack2 = ImageStack(imp.width, imp.height)

# Give user prompt to manually decide the in-focus slice for each time frame
for t in range(1, frames+1):
    gd = GenericDialog("Select in-focus slice")
    gd.addNumericField("In-focus slice for t = "+str(t), 1, 0)
    gd.showDialog()
    if gd.wasCanceled():
        raise RuntimeError("User cancelled operation.")
    in_focus_slice = int(gd.getNextNumber())

    # Add in the in-focus slice from each channel to the new stacks
    for c in range(1, channels+1):
        imp.setPosition(c, in_focus_slice, t)
        ip = imp.getProcessor().crop()
        if c == 1:
            newStack1.addSlice(str(t), ip)
        elif c == 2:
            newStack2.addSlice(str(t), ip)

# Create one stack from both image stacks
hsStack = ImageStack(imp.width, imp.height)
for i in range(1, frames+1):
    hsStack.addSlice(newStack1.getProcessor(i))
    hsStack.addSlice(newStack2.getProcessor(i))

# Convert the stack to a Hyperstack
hsImp = ImagePlus("Focus Stack", hsStack)
hsImp = HyperStackConverter().toHyperStack(hsImp, 2, 1, frames) 

# Generate an output filename and save
base = os.path.basename(img_path) # Get filename with extension
name, ext = os.path.splitext(base) # Separate filename and extension
filename = "{}_pFocus.tif".format(name) # New filename with suffix "_pFocus"
dir_path = os.path.dirname(img_path) # Get the directory path
new_path = os.path.join(dir_path, filename) # Join directory path and new filename
FileSaver(hsImp).saveAsTiffStack(new_path)

imp.close()
