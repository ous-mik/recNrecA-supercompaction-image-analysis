from ij.plugin import ChannelSplitter, RGBStackMerge, ImageCalculator, ImagesToStack, Duplicator
from ij import IJ, ImagePlus, ImageStack, WindowManager
from ij.process import ImageConverter
from ij.measure import Calibration
from ij.gui import GenericDialog
from javax.swing import JFileChooser, JFrame
from java.io import File
from javax.swing.filechooser import FileFilter
import os

class ChannelConfig:
	def __init__(self, channel_type, channel_number, do_processing):
		self.channel_type = channel_type
		self.channel_number = channel_number
		self.do_processing = do_processing

class CustomFileFilter(FileFilter):
	def __init__(self, _description, extensions):
		self._description = _description
		self.extensions = set(extensions)

	def accept(self, file):
		# Allow directories to be seen and selected
		if file.isDirectory():
			return True

		# Check if the file matches the title pattern and extensions
		filename = file.getName()
		return any(filename.endswith(ext) for ext in self.extensions)
		
	def getDescription(self):
		return self._description

def get_user_input():
	"""
    Gets the user's preferences for how each channel should be processed.
    :param num_channels: The number of channels to retrieve preferences for.
    :return: A list of ChannelConfig objects containing the user's preferences.
    """
	bf_channel = None
	fl_channel = None
	channels_config = []
	num_channels = None
    
	# Create dialog for selecting image format
	gd_fileFormat = GenericDialog("Number of Channels")
	gd_fileFormat.addNumericField("Number of Channels in images:", 2, 0) # add a numeric input for num_channels
	gd_fileFormat.showDialog()
    
	if gd_fileFormat.wasCanceled():
		return None
		
	num_channels = gd_fileFormat.getNextNumber()
	if num_channels == None:
		return None
	# Convert num_channels to an integer
	num_channels = int(num_channels)
	if num_channels != 2:
		IJ.error("Only two channels are supported.")
		return None, None
	
	for i in range(num_channels):
		gd = GenericDialog("Channel {} Configuration".format(i+1))
		gd.addChoice("Channel Type:", ["Brightfield", "Fluorescence"], "Brightfield")
		gd.addCheckbox("Do Processing?", True)
		gd.showDialog()

		if gd.wasCanceled():
			return None

		channel_type = gd.getNextChoice()
		channel_number = i
		do_processing = gd.getNextBoolean()

		if channel_type == 'Brightfield':
			if bf_channel is not None:  # If Brightfield channel already exists, show an error
				IJ.error("Only one channel can be marked as Brightfield!")
				return None
			bf_channel = i
		elif channel_type == 'Fluorescence':
			if fl_channel is not None:  # If Fluorescence channel already exists, show an error
				IJ.error("Only one channel can be marked as Fluorescence!")
				return None
			fl_channel = i

		# Save each set of user preferences into a ChannelConfig object
		channels_config.append(ChannelConfig(channel_type, channel_number, do_processing))

	if bf_channel is None and fl_channel is None:
		IJ.error("Please select at least one channel to process.")
		return None, None

	return bf_channel, fl_channel

# Function to process brightfield image as described
def process_brightfield(imp):
	# create a duplicate of the original image
	imp_duplicate = imp.duplicate() 
	IJ.run(imp_duplicate, "Median...", "radius=16") # Equals roughly 2 µm in size

	# Subtract the filtered image from the original
	ic = ImageCalculator()
	result = ic.run("Subtract create 32-bit", imp, imp_duplicate)
	
	# Set brightness levels of 32-bit result image and convert to 16-bit
	standard_min = -7500  # Minimum brightness
	standard_max = 10000  # Maximum brightness
	result.setDisplayRange(standard_min, standard_max)
	ImageConverter(result).convertToGray16()

	return result  # Return the resulting image

# Function to subtract background from fluorescence image as described
def process_fluorescence(imp):
	IJ.run(imp, "Subtract Background...", "rolling=8 sliding") # Equals roughly 1 µm in size
	return imp  # Return the processed image

def get_pixel_size(imp):
	"""Retrieves the original pixel size from an image."""
	cal = imp.getCalibration()
	return cal.pixelWidth, cal.getXUnit()

def set_scale(imp, pixel_Width, pixel_Unit):
	cal = Calibration()
	cal.pixelWidth = pixel_Width
	cal.pixelHeight = pixel_Width
	cal.setUnit(pixel_Unit)
	imp.setCalibration(cal)
	return imp

def open_and_process_image(filepath, bf_channel, fl_channel):
	imp = IJ.openImage(filepath)
	if imp is None:
		print("Error: Could not open file: ", filepath)
		return None

	# Get pixel size from the first image
	if not 'pixelWidth' in globals():
		global pixelWidth, pixelUnit
		pixelWidth, pixelUnit = get_pixel_size(imp)

	# Conditional processing based on user preferences 
	if bf_channel is not None:
		# Assuming that you do not have a z-stack or time stack:
		brightfield_image = Duplicator().run(imp, bf_channel + 1, bf_channel + 1, 1, 1, 1, 1)
		processed_brightfield = process_brightfield(brightfield_image)

	if fl_channel is not None:
		# Assuming that you do not have a z-stack or time stack:
		fluorescence_image = Duplicator().run(imp, fl_channel + 1, fl_channel + 1, 1, 1, 1, 1)
		processed_fluorescence = process_fluorescence(fluorescence_image)

	# Merge the processed channels back into a single hyperstack
	# Assuming both channels have been processed into ImagePlus objects
	channels = [processed_brightfield, processed_fluorescence]
	processed_stack = RGBStackMerge.mergeChannels(channels, False)

	# Set scale for each image
	processed_stack = set_scale(processed_stack, pixelWidth, pixelUnit)

	return processed_stack

def save_processed_image(image, original_file_path):
	directory, filename = os.path.split(original_file_path)
	name, ext = os.path.splitext(filename)
	output_filename = name + "_Processed" + ext
	output_path = os.path.join(directory, output_filename)

	# Save the image
	IJ.saveAsTiff(image, output_path)

def batch_process(files, bf_channel, fl_channel):
	for filepath in files:
		print("Processing:", filepath)
		processed_image = open_and_process_image(filepath, bf_channel, fl_channel)
		if processed_image is not None:
			save_processed_image(processed_image, filepath)

def select_files():
	# Create a file chooser
	startDir = "C:/Users/kristerv/OneDrive - Universitetet i Oslo/ImageAnalysis/Coli Inspector"
	fileChooser = JFileChooser()
	fileChooser.setCurrentDirectory(File(startDir))
	fileChooser.setMultiSelectionEnabled(True)
	fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY)

	# Create a filter for files based on title and extension
	filter = CustomFileFilter("Custom Image files", [".jpg", ".png", ".tif", ".bmp", ".gif", ".TIF", ".tiff", ".TIFF"])
	fileChooser.setFileFilter(filter)

	# Show the dialog to the user
	retval = fileChooser.showOpenDialog(JFrame())
	if retval == JFileChooser.APPROVE_OPTION:
		selectedFiles = fileChooser.getSelectedFiles()
		return [file.getAbsolutePath() for file in selectedFiles]
	else:
		return []

def main():
	filepaths = select_files()
	if not filepaths:
		IJ.error("No files were selected!")
		return

	# Get user input
	bf_channel, fl_channel = get_user_input()
	if bf_channel is None or fl_channel is None:
		return

	batch_process(filepaths, bf_channel, fl_channel)
	print("Processing completed. Original pixel size: {} {}".format(pixelWidth, pixelUnit))

if __name__ in ['__builtin__', '__main__']:
	main()
