# recNrecA-supercompaction-image-analysis

This repository contains scripts and templates used for image preprocessing and analysis in the publication specified below.

## Publication (preprint)

Krister Vikedal, Synnøve B. Ræder, Ida Mathilde Riisnæs, Magnar Bjørås, James Booth, Kirsten Skarstad, and Emily helgesen <br>
**RecN and RecA orchestrate an ordered DNA supercompaction following ciprofloxacin exposure of Escherichia coli**<br>
bioRxiv (2024)<br>
doi: 

Please see the Methods and Materials section of the paper for details on preprocessing and analysis. 

## Scripts for preprocessing

All scripts for preprocessing of images from different microscopes before analysis are located in the folder `Preprocessing`. These scripts are intended for use in the Fiji distribution of ImageJ, using Jython, an implementation of Python that runs on the Java platform. Different scripts were written for each type of microscope, due to differences in image formats and imaging methods. Each script is described under their relevant heading below. 

### Preprocessing of Z-stacks from Zeiss Axio Observer Z1

The Z-stacks were first processed using the script `FocusedZSlicePrompter.py` to select the best-focused slice from each frame, and save them as a new `.tif` hyperstack. The input hyperstack should ideally also be a `.tif` file. The images in the new in-focus hyperstack were then manually preprocessed in Fiji (ImageJ) using the procedure described in `Preprocessing_ZeissZ1_images.txt`. 

### Preprocessing of images from Nikon Eclipse Ti2-E

Images in the `.nd2` format were preprocessed using the script `Preprocessing_NikonTi2_images.py`.

A separate flat-field correction image is required for preprocessing of the brightfield channel and is optional for fluorescence channels. To create a flat-field correction image, we averaged 20 images acquired from different locations on an empty agar pad using the same microscope settings as for the images to be processed. 

### Preprocessing of images from Molecular Devices ImageXpress

Images in the `.tif` format with filenames describing well number, imaging site, and channel were preprocessed using the script `Preprocessing_ImageXpress_images.py`. The `time_map` variable needs to be modified to ensure correct `time_stamp` annotations on output image filenames. 

### Preprocessing of images from Leica DM6000 B

Images in the `.lif` format were first saved as individual `.tif` images and then preprocessed using the script `Preprocessing_DM6000B_images.py`.


## Scripts and templates for analysis

All scripts and templates for analysis of images with the Coli-Inspector and MicrobeJ plugins in Fiji (ImageJ) are located in the folder `Analysis`. 

### Modified Coli-Inspector script

We have customized the script of the ObjectJ-based [Coli-Inspector](https://sils.fnwi.uva.nl/bcb/objectj/examples/Coli-Inspector/Coli-Inspector-MD/coli-inspector.html) plugin (version 03f) to allow grouping of cells by image number and, consequently, by time frame. Please refer to the plugin's documentation for detailed instructions on its use. 

To use the customized plugin, open the file `Coli-Inspector-03f-KVmod.ojj` in Fiji (ImageJ). The changes made to the original script can be reviewed in the corresponding file `Coli-Inspector-03f-KVmod.txt`, where code modifications are annotated with the comment `Added by KV`.

### Templates for MicrobeJ


## Author

Krister Vikedal

## Acknowledgements

The customized script `Coli-Inspector-03f-KVmod.ojj` is based on the Coli-Inspector plugin (version 03f), developed by Norbert Vischer from the University of Amsterdam. The original plugin can be downloaded from the [documentation page](https://sils.fnwi.uva.nl/bcb/objectj/examples/Coli-Inspector/Coli-Inspector-MD/coli-inspector.html). ChatGPT by OpenAI was utilized for suggesting code for scripts included in this repository. 
