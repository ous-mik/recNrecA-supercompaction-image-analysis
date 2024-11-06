from ij.plugin import ChannelSplitter, RGBStackMerge, ImageCalculator, ImagesToStack, Duplicator, ZProjector, HyperStackConverter
from ij.plugin.filter import BackgroundSubtracter
from ij.plugin.frame import RoiManager
from ij import IJ, ImagePlus, ImageStack, WindowManager, VirtualStack
from ij.process import ImageConverter, FloatProcessor
from ij.measure import Calibration
from ij.gui import GenericDialog
from ij.io import FileSaver, FileInfo
from javax.swing import JFileChooser, JFrame
from java.io import File
from javax.swing.filechooser import FileFilter
from loci.plugins import BF
from loci.plugins.in import ImporterOptions, ImagePlusReader, ImportProcess
from loci.plugins.util import BFVirtualStack
from loci.formats import ChannelSeparator
from loci.formats.in import ND2Reader
import os
import uuid

class ChannelConfig:
	def __init__(self, channel_type, channel_number, do_processing):
		self.channel_type = channel_type
		self.channel_number = channel_number
		self.do_processing = do_processing

class FlatFieldConfig:
	def __init__(self, flatFieldPath, channel_number, do_fluoFlatField):
		self.flatFieldPath = flatFieldPath
		self.channel_number = channel_number
		self.do_fluoFlatField = do_fluoFlatField

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

# Function to generate a random token
def generate_random_token():
	return str(uuid.uuid4())  # Create a random UUID

def get_image_input():
	"""
    Gets the user's preferences for how each channel should be processed.
    :param num_channels: The number of channels to retrieve preferences for.
    :return: A list of ChannelConfig objects containing the user's preferences.
    """
	channels_configs = []
	num_channels = None
	processingCheck = False
    
	# Create dialog for selecting image format
	gd_fileFormat = GenericDialog("Number of Channels")
	gd_fileFormat.addNumericField("Number of Channels in images:", 3, 0) # add a numeric input for num_channels
	gd_fileFormat.showDialog()
    
	if gd_fileFormat.wasCanceled():
		return None
		
	num_channels = gd_fileFormat.getNextNumber()
	if num_channels == None:
		return None
	# Convert num_channels to an integer
	num_channels = int(num_channels)
	
	for i in range(num_channels):
		gd = GenericDialog("Channel {} Configuration".format(i+1))
		gd.addChoice("Channel {} Type:".format(i+1), ["Brightfield", "Fluorescence"], "Brightfield")
		gd.addCheckbox("Do Processing?", True)
		gd.showDialog()

		if gd.wasCanceled():
			return None

		channel_type = gd.getNextChoice()
		channel_number = i
		do_processing = gd.getNextBoolean()
		if do_processing:
			processingCheck = True

		# Save each set of user preferences into a ChannelConfig object
		channels_configs.append(ChannelConfig(channel_type, channel_number, do_processing))

	if not processingCheck:
		IJ.error("Please select at least one channel to process.")
		return None, None

	return channels_configs

def open_nd2_images_by_location(filepath, virtual=False):
	# Create options for importing
	options = ImporterOptions()
	options.setId(filepath)
	options.setAutoscale(False)
	options.setOpenAllSeries(True)

	# Set the virtual flag based on the method parameter 
	options.setVirtual(virtual)
			
	# Open the .nd2 file using the Bio-Formats importer with the specified options
	imps = BF.openImagePlus(options)
	
	return imps

def open_other_images_by_location(filepath, virtual=False):
	# Create options for importing
	options = ImporterOptions()
	options.setId(filepath)
	options.setAutoscale(False)
	options.setOpenAllSeries(True)

	# Set the virtual flag based on the method parameter 
	options.setVirtual(virtual)

	# Open the .nd2 file using the Bio-Formats importer with the specified options
	imps = BF.openImagePlus(options)

	return imps

# Function to process brightfield image as described
def process_brightfield(frame_imp, flatfield_configs, channel_No, applyGaussian, gaussRadius):
	# Find the FlatFieldConfig for the given channel number (assuming channel_No starts at 0)
	flat_field_config = next((cfg for cfg in flatfield_configs if cfg.channel_number == channel_No), None)

	if not flat_field_config:
		print("No flat field config found for channel {}.".format(channel_No + 1))
		return None
	
	# Open the flat field image
	flat_imp = IJ.openImage(flat_field_config.flatFieldPath)
	if flat_imp is None:
		print("Could not open flat field image for channel {} from: {}".format(channel_No + 1, flat_field_image_path))
		return None

	# Calculate the mean intensity of the flat field image	
	mean_flat_intensity = flat_imp.getStatistics().mean

	# Perform flat field correction on original image
	imp = frame_imp.duplicate() # Duplicate to preserve the original image
	imp.setProcessor(imp.getProcessor().convertToFloatProcessor()) # Convert to FloatProcessor

	ic = ImageCalculator()
	ffcorrected_imp =  ic.run("Divide create", imp, flat_imp)
	
	# Check if division was successful
	if ffcorrected_imp is None:
		print("Error during division operation.")
		return None

	# Scale pixel intensity values to match original image    
	ip = ffcorrected_imp.getProcessor()
	ip.multiply(mean_flat_intensity)

	# After scaling, ensure pixel values are still within the 0-4095 range
	standard_min =  0  # Minimum brightness
	standard_max = 4095  # Maximum brightness for 12-bit range image
	ip.setMinAndMax(standard_min, standard_max)  # Set the display range to 12-bit

	# Update the image and calibration
	ffcorrected_imp.setProcessor(ip)
	ffcorrected_imp.updateAndDraw()

	# Convert to 16-bit while maintaining the 12-bit range
	new_ip = ip.convertToShortProcessor()

	# Create a new ImagePlus object for the processed frame
	processed_frame = ImagePlus("Processed Frame", new_ip)
	processed_frame.setCalibration(frame_imp.getCalibration().copy())

	# Release resources associated with the flat field image
	flat_imp.flush()

	# Optionally apply Gaussian Blur
	if applyGaussian:
		IJ.run(processed_frame, "Gaussian Blur...", "sigma={}".format(gaussRadius))

	return processed_frame  # Return the resulting image

# Function to subtract background from fluorescence image as described
def process_fluorescence(frame_imp, flatfield_configs, channel_No, pixelWidth):
	# Find the FlatFieldConfig for the given channel number (assuming channel_No starts at 0)
	flat_field_config = next((cfg for cfg in flatfield_configs if cfg.channel_number == channel_No), None)
		
	if not flat_field_config:
		print("No flat field config found for channel {}.".format(channel_No + 1))
		return None
	
	if flat_field_config.do_fluoFlatField:
		# Open the flat field image
		flat_imp = IJ.openImage(flat_field_config.flatFieldPath)
		if flat_imp is None:
			print("Could not open flat field image for channel {} from: {}".format(channel_No + 1, flat_field_image_path))
			return None

		# Calculate the mean intensity of the flat field image
		mean_flat_intensity = flat_imp.getStatistics().mean

		# Save the current LUT before any conversion
		original_LUT = frame_imp.getProcessor().getLut()

		# Perform flat field correction on original image
		imp = frame_imp.duplicate() # Duplicate to preserve the original image
		imp.setProcessor(imp.getProcessor().convertToFloatProcessor()) # Convert to FloatProcessor

		ic = ImageCalculator()
		ffcorrected_imp =  ic.run("Divide create", imp, flat_imp)

		if ffcorrected_imp is None:
			print("Error during division operation.")
			return None

		# Scale pixel intensity values to match original image    
		ip = ffcorrected_imp.getProcessor()
		ip.multiply(mean_flat_intensity)

		# After scaling, ensure pixel values are still within the 0-4095 range
		standard_min =  0  # Minimum brightness
		standard_max = 4095  # Maximum brightness for 12-bit range image
		ip.setMinAndMax(standard_min, standard_max)  # Set the display range to 12-bit

		# Update the image and calibration
		ffcorrected_imp.setProcessor(ip)
		ffcorrected_imp.updateAndDraw()

		# Convert to 16-bit while maintaining the 12-bit range
		new_ip = ip.convertToShortProcessor()

		# Create a new ImagePlus object for the processed frame
		processed_frame = ImagePlus("Processed Frame", new_ip)
		processed_frame.setCalibration(frame_imp.getCalibration().copy())

		# Release resources associated with the flat field image
		flat_imp.flush()

		# Restore the original LUT to the corrected image
		processed_frame.getProcessor().setLut(original_LUT)
		processed_frame.updateAndDraw()
	else:
		processed_frame = frame_imp

	micron_size = round(1/pixelWidth)
	IJ.run(processed_frame, "Subtract Background...", "rolling={} sliding".format(micron_size)) # Equals  1 µm in size

	return processed_frame  # Return the processed image

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

def open_image(filepath, largefile):
	# Check if the file is an .nd2 file by the file extension
	if filepath.endswith(".nd2"):
		imps = open_nd2_images_by_location(filepath, virtual=largefile)
	else:
		imps = open_other_images_by_location(filepath, virtual=largefile)

	if not imps or any(imp is None for imp in imps):
		print("Error: Could not open file: ", filepath)
		return None

	return imps

def process_image(imp, channels_configs, flatfield_configs, applyGaussian, gaussRadius, temp_dir_path, location_index):
	# Get pixel size from the first image
	pixel_frame = Duplicator().run(imp, 1, 1, 1, 1, 1, 1)
	pixelWidth, pixelUnit = get_pixel_size(pixel_frame)
	pixel_frame.close()
	
	total_time_frames = imp.getNFrames()
	print("Total time frames: {}".format(total_time_frames))
	
	# Generate a random token at the start of the process
	random_token = generate_random_token()
	print("Random token added to temp files: {}".format(random_token))

	# List to hold file paths to the processed frames for each channel
	channel_frame_paths = [[] for _ in channels_configs]
	#channels = [[] for _ in channels_configs]  # List to hold processed frames for each channel

	for frame_no in range(1, total_time_frames + 1):
		for ch_config in channels_configs:
			frame = Duplicator().run(imp, ch_config.channel_number + 1, ch_config.channel_number + 1, 1, 1, frame_no, frame_no)

			if ch_config.do_processing:
				if ch_config.channel_type == "Brightfield":
					processed_frame = process_brightfield(frame, flatfield_configs, ch_config.channel_number, applyGaussian, gaussRadius)
				elif ch_config.channel_type == "Fluorescence":
					processed_frame = process_fluorescence(frame, flatfield_configs, ch_config.channel_number, pixelWidth)
			else:
				processed_frame = frame
			
			processed_frame = set_scale(processed_frame, pixelWidth, pixelUnit)
   
			# Save the processed frame to disk
			frame_filename = "{}_frame{}_channel{}_Loc{}.tif".format(random_token, frame_no, ch_config.channel_number, location_index)
			frame_filepath = os.path.join(temp_dir_path, frame_filename)
			fs = FileSaver(processed_frame)
			fs.saveAsTiff(frame_filepath)

			# Close the processed frame to free memory
			processed_frame.close()

			# Store the file path
			channel_frame_paths[ch_config.channel_number].append(frame_filepath)

	# # Reconstruct the channels into full stacks
	# channel_stacks = []
	# for channel_frames in channels:
	# 	channel_stack = ImageStack(imp.width, imp.height)
	# 	for frame in channel_frames:
	# 		channel_stack.addSlice(frame.getProcessor())
	# 	channel_stacks.append(ImagePlus("Channel Stack", channel_stack))

	# # Merge the processed channels back into a single hyperstack
	# processed_stack = RGBStackMerge.mergeChannels(channel_stacks, False)

	# # Set scale for each image
	# processed_stack = set_scale(processed_stack, pixelWidth, pixelUnit)

	return channel_frame_paths, pixelWidth, pixelUnit

def cleanup_temp_directory(temp_dir, location_index):
	# Delete all files in the temp_dir for the specified location_index
	for filename in os.listdir(temp_dir):
		# Construct the full file path
		file_path = os.path.join(temp_dir, filename)
		# Check if this file is part of the current location index being processed
		if filename.endswith("Loc{}.tif".format(location_index)):
			try:
				# If it's a file, delete it
				if os.path.isfile(file_path):
					os.remove(file_path)
			except Exception as e:
				print("Error while deleting file {}: {}".format(file_path, e))

def save_processed_image(channel_frame_paths, original_file_path, applyGaussian, multiLoc, location_index):
	# Prepare an output file path for the full processed stack
	directory, original_filename = os.path.split(original_file_path)
	filename, _ = os.path.splitext(original_filename)
	if applyGaussian:
		output_filename_init = filename + "_FlatFieldCorr_GBlur"
	else:
		output_filename_init = filename + "_FlatFieldCorr"

	if multiLoc:
		output_filename = output_filename_init + "_Loc{}".format(location_index+1) + ".tif"
	else: 
		output_filename = output_filename_init + ".tif"
	
	output_file_path = os.path.join(directory, output_filename)

	# Initialize a list to keep ImagePlus objects for each channel
	channel_stacks = []
	
	# Determine final size of hyperstack
	nChannels = len(channel_frame_paths)
	nFrames = len(channel_frame_paths[0])

	# Load and stack each channel's processed frames
	for ch_paths in channel_frame_paths:
		# Initialize an empty ImageStack for the current channel
		channel_stack = None
		for frame_path in ch_paths:
			# Open each frame as an ImagePlus object
			processed_frame = IJ.openImage(frame_path)

			# Create an ImageStack if it's the first frame for this channel
			if channel_stack is None:
				channel_stack = ImageStack(processed_frame.getWidth(), processed_frame.getHeight())
			
			# Add the current frame to the channel stack
			channel_stack.addSlice(processed_frame.getProcessor())

			# Close the frame to free memory
			processed_frame.close()
		
		# Convert ImageStack to ImagePlus and add to the list of channel stacks
		channel_stacks.append(ImagePlus("Channel {}".format(len(channel_stacks)+1), channel_stack))

	# Merge the channel stacks into a single RGB hyperstack (if needed)
	if len(channel_stacks) > 1:
		# Use RGBStackMerge without creating composite
		processed_hyperstack = RGBStackMerge().mergeChannels(channel_stacks, False)
	else:
		# For single channel, there's no need for merging
		processed_hyperstack = channel_stacks[0]
	
	# Create a hyperstack with the correct dimensions (nChannels x 1 x nFrames)
	processed_hyperstack.setDimensions(nChannels, 1, nFrames)
	processed_hyperstack = HyperStackConverter.toHyperStack(processed_hyperstack, nChannels, 1, nFrames, "xyczt(default)", "Color")
	
	# Set metadata and pixel size for new hyperstack
	cal_frame = IJ.openImage(channel_frame_paths[0][0])
	processed_hyperstack.setCalibration(cal_frame.getCalibration().copy())
	cal_pixelWidth, cal_pixelUnit = get_pixel_size(cal_frame)
	processed_hyperstack = set_scale(processed_hyperstack, cal_pixelWidth, cal_pixelUnit)
	cal_frame.close()

	# Save the full processed stack to disk
	FileSaver(processed_hyperstack).saveAsTiff(output_file_path)

	# Close the processed hyperstack to free up memory
	processed_hyperstack.close()
	IJ.run("Collect Garbage")
	
	return output_filename_init

def is_large_file(filepath, threshold_bytes=1073741824): # 1 GB in bytes
	try:
		size = os.path.getsize(filepath)
	except os.error as e:
		print("Error accessing file '{}':".format(filepath), e)
		return True  # Can't ascertain size
	return size > threshold_bytes

def delete_empty_directory(directory_path):
	if os.path.exists(directory_path) and os.path.isdir(directory_path):
		if not os.listdir(directory_path):  # Check if directory is empty
			try:
				os.rmdir(directory_path)  # Remove the directory
			except OSError as e:
				print("Error: {} could not be deleted. Exception: {}".format(directory_path, e))

def batch_process(files, channels_configs, flatfield_configs, applyGaussian, gaussRadius):
	processed_image = None
	output_filename_init = ""
	for filepath in files:
		print("Processing:", filepath)
		largefile = is_large_file(filepath)
		opened_images = open_image(filepath, largefile)
		multiLoc = len(opened_images) > 1 if opened_images else False
		directory, _ = os.path.split(filepath) # Use directory of image for storing temporary files
		temp_dir_path = os.path.join(directory, "temp_dir")
		
		# Create a temporary directory for saving processed frames if it doesn't exist
		if not os.path.exists(temp_dir_path):
			os.makedirs(temp_dir_path)
		
		if opened_images:
			for i, imp in enumerate(opened_images):
				if multiLoc:
					print("Processing location {}".format(i + 1)) 
				else:
					print("Processing image")
				# Process the image and save the results
				channel_frame_paths, pixelWidth, pixelUnit = process_image(imp, channels_configs, flatfield_configs, applyGaussian, gaussRadius, temp_dir_path, i if multiLoc else 0)
				if channel_frame_paths is not None:
					output_filename_init = save_processed_image(channel_frame_paths, filepath, applyGaussian, multiLoc, i if multiLoc else 0)

				# Cleanup temp directory by deleting temporary files
				cleanup_temp_directory(temp_dir_path, i if multiLoc else 0)

			if channel_frame_paths is not None:
				print("Saved image(s): {}".format(output_filename_init) + "\nOriginal pixel size: {} {}".format(pixelWidth, pixelUnit))

		# After processing all locations, delete the temp directory if it is empty
		delete_empty_directory(temp_dir_path)
		IJ.run("Collect Garbage")

def get_gaussian_input():
	gd_gauss = GenericDialog("Gaussian Blur filter application")
	gd_gauss.addCheckbox("Apply Gaussian Blur filter to Brightfield channel?", True)
	gd_gauss.addNumericField("Sigma (Radius):", 1, 2)
	gd_gauss.showDialog()

	if gd_gauss.wasCanceled():
		return False

	applyGaussian = gd_gauss.getNextBoolean()
	gaussRadius = gd_gauss.getNextNumber()

	if applyGaussian is None or gaussRadius is None:
		return False

	return applyGaussian, gaussRadius

def get_flatfield_paths(channels_configs):
	flatfield_configs = []
	FLATFIELD_BG_SUBTRACTION = "Flat Field Correction + Background subtraction"
	ONLY_BG_SUBTRACTION = "Only Background subtraction"
	
	# Get paths for all flatfield images
	flatStartDir = "E:/Nikon Eclipse microscope/Background illumination controls/FlatField Correction"
	gd_flatField = GenericDialog("Choose Flat Field image for each channel")
	for ch_config in channels_configs:
		if ch_config.do_processing:
			gd_flatField.addFileField("Channel {} Flat Field image".format(ch_config.channel_number + 1), flatStartDir)
			if ch_config.channel_type == "Fluorescence":
				gd_flatField.addChoice("Channel {} pre-processing method:".format(ch_config.channel_number + 1), [FLATFIELD_BG_SUBTRACTION, ONLY_BG_SUBTRACTION], FLATFIELD_BG_SUBTRACTION)
	gd_flatField.showDialog()

	if gd_flatField.wasCanceled():
		return None

	for ch_config in channels_configs:
		if ch_config.do_processing:
			flatFieldPath = gd_flatField.getNextString()
			if ch_config.channel_type == "Fluorescence":				
				do_fluoFlatField = gd_flatField.getNextChoice() == FLATFIELD_BG_SUBTRACTION
			else: 
				do_fluoFlatField = True
			flatfield_configs.append(FlatFieldConfig(flatFieldPath, ch_config.channel_number, do_fluoFlatField))

	return flatfield_configs

def select_files():
	# Create a file chooser
	#startDir = "C:/Users/kristerv/OneDrive - Universitetet i Oslo/ImageAnalysis"
	startDir = "E:/Nikon Eclipse microscope"
	fileChooser = JFileChooser()
	fileChooser.setCurrentDirectory(File(startDir))
	fileChooser.setMultiSelectionEnabled(True)
	fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY)

	# Create a filter for files based on title and extension
	filter = CustomFileFilter("Custom Image files", [".nd2", ".tif", ".TIF", ".tiff", ".TIFF"])
	fileChooser.setFileFilter(filter)

	# Show the dialog to the user
	retval = fileChooser.showOpenDialog(JFrame())
	if retval == JFileChooser.APPROVE_OPTION:
		selectedFiles = fileChooser.getSelectedFiles()
		return [file.getAbsolutePath() for file in selectedFiles]
	else:
		return []
	
def close_all_images():
	"""Close all open image windows in ImageJ."""
	if WindowManager.getWindowCount() > 0:
		IJ.run("Close All")
	IJ.run("Collect Garbage")

def main():
	gd_clear = GenericDialog("Clear open image files")
	gd_clear.addMessage("This process will close all currently open image windows. Do you want to proceed?")
	gd_clear.enableYesNoCancel()
	gd_clear.showDialog()	
	if gd_clear.wasCanceled(): # User pressed "Cancel" or closed the dialog
		return 
	elif gd_clear.wasOKed(): # User pressed "Yes"
		close_all_images()
		
	gd_message = GenericDialog("ND2 preprocessing")
	gd_message.addMessage("Select all files from Nikon microscope for preprocessing. All images should have the same channel layout and use the same acquisition settings.")
	gd_message.setOKLabel("Browse")
	gd_message.showDialog()
	if gd_message.wasCanceled():
		return 

	filepaths = select_files()
	if not filepaths:
		IJ.error("No files were selected!")
		return

	# Get user input
	channels_configs = get_image_input()
	if not channels_configs:
		return

	flatfield_configs = get_flatfield_paths(channels_configs)

	if flatfield_configs is None:
		print("Flat field configuration was canceled by user.")
		return

	# Iterate over flatfield configurations and check that every config
	# that requires flat field correction has a non-empty path.
	for cfg in flatfield_configs:
		if cfg.do_fluoFlatField and not cfg.flatFieldPath.strip():
			IJ.error("Missing flat field image path for channel {}.".format(cfg.channel_number + 1))
			return

	# Check for identical flatFieldPaths
	path_to_channels = {}
	for cfg in flatfield_configs:
		if cfg.do_fluoFlatField:  # Check only if flat field correction is to be done
			path = cfg.flatFieldPath.strip()
			if path in path_to_channels:
				path_to_channels[path].append(cfg.channel_number)
			else:
				path_to_channels[path] = [cfg.channel_number]
	
	# Identify paths that are used for multiple channels
	duplicate_paths = {path: ch_nums for path, ch_nums in path_to_channels.items() if len(ch_nums) > 1}

	if duplicate_paths:
		# Construct a message to prompt the user
		message = "The following flat field images are used for multiple channels:\n"
		for path, ch_nums in duplicate_paths.items():
			message += "Path: {} - Channels: {}\n".format(path, ', '.join(str(num + 1) for num in ch_nums))
		message += "Is it okay to continue with processing?"

		# Ask the user for confirmation
		gd_duplicate = GenericDialog("Duplicate Flat Field Images")
		gd_duplicate.addMessage(message)
		gd_duplicate.enableYesNoCancel()
		gd_duplicate.showDialog()
		if gd_duplicate.wasCanceled():
			return
		elif not gd_duplicate.wasOKed():  # User pressed "No"
			print("User chose not to proceed with duplicate flat field paths.")
			return  # Exit if the user does not want to continue

	applyGaussian, gaussRadius = get_gaussian_input()

	batch_process(filepaths, channels_configs, flatfield_configs, applyGaussian, gaussRadius)
	print("Processing completed")
	IJ.run("Collect Garbage")

if __name__ in ['__builtin__', '__main__']:
	main()
