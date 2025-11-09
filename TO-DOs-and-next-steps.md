# Status as of 11/3/2025

## Lots of progress has been made:
1. Python scripts for generating images is working well and updated to take style (theme) and many effects palettes to generate images.
2. Images and loadable JSON files generated for almost all fundamental types for Cybermancy.
3. 3 separate scripts to load weapons, reskin existing DH objects, and generate loadable JSON from an Excel file, including basic action config.
4. Learned lots about how the DH JSON is structured

## TO DOs:
 - Extract the Foundry folder path and include as part of the item listings
 - Extract the tier from the folders, if there is not tier value (e.g. cybernetics)
 - For class and subclass, populate those item listings with the image, name and description of the linked features - this will require building a feature dictionary with the ids and dynamically linking them in - not exactly sure how I'm going to do that... 


 - Drone mods - should be in the same most as weapon mods, just load the object, description, and image then manually make the details as needed.
 - Build the first Adversaries and Environments by hand... 
 - ... which means, start writing the big picture story, so you know which to build first.
 - Hand rebuild the 3 new classes, because that clearly never got done.
 - Use foundrycli tools to unpack the Compendium packs and check into Github.
 - Use the unpacked JSON from the foundrycli to use as the basis for starting to generate the web pages to share with the guys.
 - Reach out to the Frag Maps artist and offer to help build that compendium pack?
 - Reach out to DH / Foundryborne and see if the have advice / help about how to proceed efficiently.

## Story writing:

 - 

## FUTURE:
 - Refactor the JSON generator code to be 1 script rather than 3.
 - Figure out how to extend DH module to support:
 - - stacked armor, cybernetics and worn armor.
 - - energy weapons
 - - 