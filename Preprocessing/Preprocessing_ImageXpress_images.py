from ij import IJ, ImagePlus, ImageStack, WindowManager
from ij.plugin import ChannelSplitter, RGBStackMerge, ImageCalculator, ImagesToStack
from ij.process import ImageConverter
from ij.gui import GenericDialog
from ij.io import DirectoryChooser, OpenDialog
from ij.measure import Calibration
from java.awt import Frame
from javax.swing import JFileChooser, JFrame
from javax.swing.filechooser import FileFilter
from java.lang import String
from java.nio.charset import Charset
from java.io import File
import os

# Helper class to manage the channel information
class ChannelConfig:
	def __init__(self, channel_type, channel_number, do_processing):
		self.channel_type = channel_type
		self.channel_number = channel_number
		self.do_processing = do_processing

class CustomFileFilter(FileFilter):
	def __init__(self, _description, extensions, titlePattern):
		self._description = _description
		self.extensions = set(extensions)
		self.titlePattern = titlePattern

	def accept(self, file):
		# Allow directories to be seen and selected
		if file.isDirectory():
			return True

		# Check if the file matches the title pattern and extensions
		filename = file.getName()
		# Use 'in' operator instead of 'endswith()' to allow titlePattern anywhere in the file name
		return any(filename.endswith(ext) for ext in self.extensions) and self.titlePattern in filename
		
	def getDescription(self):
		return self._description

# Time mapping based on the first letter in the well ('C' to 'N')
time_map = {
	'C': "10min",
	'D': "20min",
	'E': "30min",
	'F': "40min",
	'G': "50min",
	'H': "60min",
	'I': "70min",
	'J': "80min",
	'K': "90min",
	'L': "100min",
	'M': "110min",
    'N': "120min" 
}

# Modified map for Supercomp timing screening
time_map_SuperComp = {
	'03': "I37T42_Cip20min",
	'04': "I37T42_Cip40min",
	'05': "I37T42_Cip60min",
	'06': "I42T42_Untreated",
	'07': "I42T42_Cip20min",
	'08': "I42T42_Cip40min",
	'09': "I42T42_Cip60min",
	'12': "I30T37_Cip20min",
	'13': "I30T37_Cip40min",
	'14': "I30T37_Cip60min",
	'15': "I30T42_Cip20min",
	'16': "I30T42_Cip40min",
	'17': "I30T42_Cip60min",
	'18': "I37T37_Untreated",
	'19': "I37T37_Cip20min",
	'20': "I37T37_Cip40min",
	'21': "I37T37_Cip60min",
	'22': "I37T42_Cip20min",
    '23': "I37T42_Cip60min" 
}

def select_files():
	# Allow user to choose filter for well_number
	gd_wellnumber = GenericDialog("Select filter text for file browsing")
	gd_wellnumber.addStringField("Filter text:", "_O") # Adjust this to the relevant number/letter for the wells you want
	gd_wellnumber.showDialog()
	if gd_wellnumber.wasCanceled():
		return None
	well_number = gd_wellnumber.getNextString()
	
	# Create a file chooser
	startDir = "E:/ImageXpress microscope/SupercompactionTiming/240115_Plate_7577/TimePoint_1"
	fileChooser = JFileChooser()
	fileChooser.setCurrentDirectory(File(startDir))
	fileChooser.setMultiSelectionEnabled(True)
	fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY)

	# Create a filter for files based on title and extension
	filter = CustomFileFilter("Custom Image files", [".jpg", ".png", ".tif", ".bmp", ".gif", ".TIF", ".tiff", ".TIFF"], well_number)
	fileChooser.setFileFilter(filter)

	# Show the dialog to the user
	retval = fileChooser.showOpenDialog(JFrame())
	if retval == JFileChooser.APPROVE_OPTION:
		selectedFiles = fileChooser.getSelectedFiles()
		return [file.getAbsolutePath() for file in selectedFiles]
	else:
		return []

def get_user_input():
	"""
    Gets the user's preferences for how each channel should be processed.
    :param num_channels: The number of channels to retrieve preferences for.
    :return: A list of ChannelConfig objects containing the user's preferences.
    """
	bf_channel = None
	fl_channels = []
	channels_config = []
	num_channels = None
    
	# Create dialog for selecting image format
	gd_fileFormat = GenericDialog("File Format Configuration and Number of Channels")
	gd_fileFormat.addChoice("Image format:", ["ImageXpress", "Other"], "ImageXpress")
	gd_fileFormat.addNumericField("Number of Channels in images:", 2, 0) # add a numeric input for num_channels
	gd_fileFormat.showDialog()
    
	if gd_fileFormat.wasCanceled():
		return None
    
	# Check the selected image format
	image_format = gd_fileFormat.getNextChoice()
	if image_format == "Other":
		IJ.error("This script can currently only process image files from ImageXpress")
		return None  # Ends the script if the selected format is not supported
		
	num_channels = gd_fileFormat.getNextNumber()
	if num_channels == None:
		return None
	# Convert num_channels to an integer
	num_channels = int(num_channels)
	
	for i in range(num_channels):
		gd = GenericDialog("Channel {} Configuration".format(i+1))
		gd.addChoice("Channel Type:", ["Brightfield", "Fluorescence"], "Fluorescence")
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
			fl_channels.append(i)

		# Save each set of user preferences into a ChannelConfig object
		channels_config.append(ChannelConfig(channel_type, channel_number, do_processing))

	# The final list of channels mentioned should place the Brightfield channel first (if it exists)
	final_channels_order = []
	if bf_channel is not None:
		final_channels_order.append(bf_channel)
	final_channels_order.extend(fl_channels)

	return [channels_config[i] for i in final_channels_order], image_format, num_channels

# Function to process brightfield image as described
def process_brightfield(imp):
	# create a duplicate of the original image
	imp_duplicate = imp.duplicate() 
	IJ.run(imp_duplicate, "Median...", "radius=18") # Equals roughly 2 µm in size

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
	IJ.run(imp, "Subtract Background...", "rolling=9 stack") # Equals roughly 1 µm in size
	return imp  # Return the processed image

# Revised parse_filename function with simple error handling
def parse_filename(filename):
	try:
		parts = filename.split('_')
		# Depending on the actual format, this could need more robust error checking
		return {
			'date': parts[0],
			'well': parts[1],
			'site': parts[2][1],
			'channel': int(parts[3][1])
		}
	except (IndexError, ValueError) as e:
		print("Error parsing filename: {}".format(e))
		return None

def merge_channels(*stacks):
	# Merge all input stacks into a single hyperstack
	merged = RGBStackMerge.mergeChannels(stacks, False)
	return merged

def set_scale(imp, pixelWidth, pixelUnit):
	cal = Calibration()
	cal.pixelWidth = pixelWidth
	cal.pixelHeight = pixelWidth
	cal.setUnit(pixelUnit)
	imp.setCalibration(cal)
	return imp

def main():
	filepaths = select_files()
	if not filepaths:
		IJ.error("No files were selected!")
		return
    
	# Get user input considering modifications for the brightfield channel
	user_input = get_user_input()
	if user_input is None:  # Stop the script if the user input is invalid
		print("User input canceled or invalid.")
		return
	channels_config, image_format, num_channels = user_input

	# Define output location
	dc = DirectoryChooser("Choose Output Directory")
	output_dir = dc.getDirectory()

	# Set scaling values
	pixelWidth = 0.115
	pixelUnit = u"µm"

	# Initialize data structures for organizing images
	sites = {}
    
	# Process and organize files
	for filepath in filepaths:
		file_name = os.path.basename(filepath)
		metadata = parse_filename(file_name)
		if metadata is None:
			print("Skipping file due to parsing error: ", filename)
			continue
        
		well = metadata['well']
		site = metadata['site']
		channel = metadata['channel']
		image_date = metadata['date'] 
        
		if well not in sites:
			sites[well] = {}
		if site not in sites[well]:
			sites[well][site] = [None]*num_channels
        
		# Process images based on type and user preference
		imp = IJ.openImage(filepath)
		
		channel_idx = [config.channel_number for config in channels_config].index(channel-1) # Adjust index based on new channel order
		if channels_config[channel_idx].do_processing:
			if channels_config[channel_idx].channel_type == "Brightfield":
				imp = process_brightfield(imp)
			elif channels_config[channel_idx].channel_type == "Fluorescence":
				imp = process_fluorescence(imp)

		sites[well][site][channel_idx] = imp  # Use the new index for placing the image
    
	# Create and save hyperstacks
	for well, sites_channels in sites.items():
		# Store images per channel
		stacks_per_channel = [[] for _ in range(num_channels)]

		for site, channels_images in sorted(sites_channels.items()):
			for ch_idx, img in enumerate(channels_images):
				if img is not None:
					stacks_per_channel[ch_idx].append(img)

		# Combine images to stacks
		combined_stacks = [ImagesToStack.run(stacks) for stacks in stacks_per_channel if stacks]

		# Merge channels into a hyperstack
		hyperstack = merge_channels(*combined_stacks)
		
		# Set scale for each image
		hyperstack = set_scale(hyperstack, pixelWidth, pixelUnit)  # Add this line before saving the image
		
		# Timestamp generation based on well letter
		# well_letter = well[0]  # Assuming 'well' format starts with a letter
		well_number = well[1] + well[2]  # Assuming 'well' format ends with a number
		# Get the appropriate time string for the well_letter from the mapping
		time_stamp = time_map_SuperComp.get(well_number, "UnknownTiming")

		# Save the hyperstack
		output_path = os.path.join(output_dir, "{}_{}_{}_Hyperstack.tif".format(image_date, well, time_stamp))
		IJ.saveAsTiff(hyperstack, output_path)
		
	print(u"Images were scaled: 1 pixel = {} µm.".format(pixelWidth))
	print("Processing completed.")

if __name__ in ['__builtin__', '__main__']:
	main()