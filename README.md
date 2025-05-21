# recNrecA-supercompaction-image-analysis

This repository contains scripts and templates used for image preprocessing and analysis in the publication specified below.


## Publication

Krister Vikedal, Synnøve Brandt Ræder, Ida Mathilde Marstein Riisnæs, Magnar Bjørås, James Alexander Booth, Kirsten Skarstad, and Emily helgesen <br>
**RecN and RecA orchestrate an ordered DNA supercompaction response following ciprofloxacin-induced DNA damage in <i>Escherichia coli</i>**<br>
<i>Nucleic Acids Research</i> (2025)<br>
doi: [10.1093/nar/gkaf437](https://doi.org/10.1093/nar/gkaf437)

Please see the Material and Methods section of the paper for details on preprocessing and analysis. 


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

_See License Details_

All scripts and templates for analyzing images with the ObjectJ project [Coli-Inspector](https://sils.fnwi.uva.nl/bcb/objectj/examples/Coli-Inspector/Coli-Inspector-MD/coli-inspector.html) and the [MicrobeJ](https://www.microbej.com/) plugin in Fiji (ImageJ) are located in the folder `Analysis`. 

### Modified Coli-Inspector script

We have customized the embedded macros of the ObjectJ project Coli-Inspector (version 03f) to allow grouping of cells by image number and, consequently, by time frame. To use the customized embedded macros, open the file `Coli-Inspector-03f-KVmod.ojj` in Fiji (ImageJ). The changes made to the original embedded macros can be reviewed in the corresponding file `Coli-Inspector-03f-KVmod.txt`, where code modifications are annotated with the comment `Added by KV`.

Please refer to the project's documentation for detailed instructions on its use. 

### Templates for MicrobeJ

In our study, we used two different versions of MicrobeJ for image analysis: 
- **Main version 5.13p (1):** For creating kymographs and analyzing DNA distribution.
- **Beta version 5.13p (13):** For tracking GFP-RecN and RecA-mCherry foci and analyzing their distribution and localization within cells. Also for classifying DNA compaction phenotypes.

**Templates for analyzing all cells from each time frame:** 
- `MJtemplate_AvgKymograph.xml`: To create kymographs.
- `MJtemplate_RecNinDNA_tracking.xml`: To track RecN and assess its colocalization with DNA. 
- `MJtemplate_RecAcolRecN_tracking.xml`: To track RecA and assess its colocalization with RecN.
- `MJtemplate_ClassifyDNAcompactionPhenotypes.xml`: For classifying and comparing DNA compaction phenotypes.

**Templates for single-cell analysis:** 
- `MJtemplate_SingleCell_Kymograph_Profile.xml`: To create kymographs and analyze DNA distribution profiles for strains harboring only HU-mCherry. 
- `MJtemplate_SingleCell_Kymograph_RecNinDNA_tracking.xml`: To create kymgographs and track GFP-RecN for strains harboring GFP-RecN and HU-mCherry. 
- `MJtemplate_SingleCell_Kymograph_RecNonly_tracking.xml`: To create kymographs and track GFP-RecN for strains harboring GFP-RecN and RecA-mCherry.
- `MJtemplate_SingleCell_RecAcolRecN_tracking.xml`: To track RecA-mCherry for strains harboring GFP-RecN and RecA-mCherry.

Please refer to the plugin's documentation for detailed instructions on its use. 


## License Details

Scripts for preprocessing and the modifications to the Coli-Inspector macro script in this repository are licensed under the MIT license, included in the `LICENSE` file. Templates for MicrobeJ are also licensed under the MIT license, but note that the license applies exclusively to the contributions made by the author of this repository. 

Permissions to distribute the MicrobeJ templates have been requested from the original developer, but have not yet been granted or denied. Only the modifications are currently under the MIT license, and the original software remains under its respective rights held by the original developers. Users of the templates should respect the original licensing terms of the MicrobeJ software until full permissions are obtained. 

## Author

Krister Vikedal

## Acknowledgements

The customized embedded macros `Coli-Inspector-03f-KVmod.ojj` is based on the ObjectJ project Coli-Inspector (version 03f), developed by Norbert Vischer (University of Amsterdam). The original embedded macros can be downloaded from the [documentation page](https://sils.fnwi.uva.nl/bcb/objectj/examples/Coli-Inspector/Coli-Inspector-MD/coli-inspector.html). MicrobeJ was developed by Adrien Ducret (Université de Lyon), Yves Brun (Indiana University), and Christophe Grangeasse (Université de Lyon). The plugin can be downloaded from its [download website](https://www.microbej.com/download-2/). We thank Adrien Ducret (Université de Lyon) for assistance with MicrobeJ analysis and code development for tracking of foci, and Thierry Oms (Université Libre de Bruxelles) for assistance with kymograph plots. ChatGPT by OpenAI was utilized for suggesting code for scripts included in this repository.
