
# Project update and notes 11/9/2025

At this point, I have almost all the compendia done, have sketched out the world background, and have a first cut at the corporations, the Council, and the Cabal.  Now it is time to start writing the story, the first encounter, the first mission and the first environments

### TO DOs (11/9/2025)

 - Drone mods
 - All items should have a "hide-ability" concept associated and indicates which Item Loadout they can be included in this will be a bit difficult to add post-hoc, but something to play around with.  This needs to be written up as a rules doc and should borrow from the Blades in the Dark "Item Loadout" concept.
 - Common items
 - Flashbacks - I love the idea from BitD, so write this up as a rule in Cybermancy as well, and the concept of Stress plays perfectly.
 - Start to consolidate the initial World, NPC, Corp, Cabal, and Council notes into .md pages checked into Github (and hyperlinked)
 - Write up the first mission (steal an item from a low-level corp facility - associated with one of the Council or Cabal projects - they will meet one of the 2 catalysts)
 - Write up the first encounter (get the mission and rescue / protect the mission giver from a gang or corp drop-cop unit)
 - Write up the first environment (the diner where the mission is given)
 - Write up the first chase environment (get away from the gang with the mission giver)
 - Ancestories changes in Cybermancy 
 - Community changes in Cybermancy (and new ones if needed)

### MVP release steps:

 - Player-facing world history notes
 - Player-facing corp notes
 - Player-facing faction notes
 - Player

## Key observations

1. All Compendia content needs to be internally referenced, meaning they cannot be references to Items.  References to Other Compendia are acceptable, but make a dependency that needs to be recorded in the modules.json file.
2. All things within Foundry VTT have an internally generated UUID that must come from Foundry, meaning all things must be created in Foundry or Imported through a Macro, then filed into Compendia (I wonder if there is a "Load directly to Compendia" option? - there is, but I'm not convinced that that is needed in the end)

There are 3 patterns that are emerging from this work:

### Build within Foundry VTT:
  - For some Items there really is not need or value for trying to use a scripted approach.  This generally applies to:
    - Class
    - Subclasses
    - Other Items that are low cardinality
    - For these Items the path is to build the Item directly within Foundry VTT and use drag-and-drop to configure in subordinate Items (e.g. Features, Subclasses, etc.)

### Build by "re-skinning" Daggerheart:
  - For some Items, the original Daggerheart things are perfectly fine and the only real need is a new "skin" (meaning Name, Description, and icon image). Example are:
    - Armor
    - Consumables
    - Loot
    - For these items, the path is to:
      1. Access the relevant item folder from daggerheart (e.g. `E:\Documents\Daniel\role-gaming\Cybermancy module development\daggerheart-main\daggerheart-main\src\packs\items\armors`) and make a .zip file out of it.
      2. Load to ChatGPT with a prompt like "extract the name from the uploaded .zip file and make a new name and description based on the Cybermancy world and deliver that as a rename .csv file.  Include a stubbed image name based on the new Item name".
      - Alternative path: copy paste the list from https://daggerheart.org/reference
      3. Run `pyCybermancy\retitle_armors_and_zip.py` using the rename .csv file and the folder of original JSON files.
      4. Run `pyCybermancy\batch-image-generation-on-OpenAI.py` to generate the new images automatically.
```py .\batch-image-generation-on-OpenAI.py -i armors_rename_list.json -o armor-icons --model gpt-image-1-mini --effect-key type --name-key new_name --desc-key new_new_description --max-items 5```
       5. Move the JSON files to the appropriate `cybermancy\src-loadable` subdirectory.
       6. Open Foundry VTT and run the `Validate and Load Folder` macro.
       7. File all the new Items in the right Compendia.

### Build from a "descriptor" file:
  - For some Items, the Daggerheart things won't do (e.g. guns).  For those, I have build a descriptor file and set of scripts to convert a CSV into a set of JSON files.
    - Weapons
    - Cybernetics
    - Drones and Devices
    - For these items, the path is to:
      1. From the Master list `pyCybermancy\cybermancy-object-list.xlsx`, export the relevant sheet as a .csv file.
      2. Run `pyCybermancy\convert-descriptors-to-loadable.py` using the rename .csv file and the folder of original JSON files.
      4. Run `pyCybermancy\batch-image-generation-on-OpenAI.py` to generate the new images automatically.
      5. Move the JSON files to the appropriate `cybermancy\src-loadable` subdirectory.
      6. Open Foundry VTT and run the `Validate and Load Folder` macro.
      7. File all the new Items in the right Compendia.

## Other utility scripts:

 - `pyCybermancy\convert_and_resize_png_to_webp.py` - Just what it says, replace in situ a .png file with a.webp file:

``` py .\\convert_and_resize_png_to_webp.py --width 400 --height 400 --dpi 96 --quality 8 --lossless --recursive ..\assets\icons\```

 - `pyCybermancy\organize-by-tier.py` - Take a set of Item JSON files and reorganize them by tier into subfolders for easy loading.

```py organize-by-tier.py E:\FoundryVTT\Data\modules\cybermancy\src-loadable\items\armors```

 - `tar -a -c -f cybermancy.zip --exclude=cybermancy/.git --exclude=cybermancy/node_modules --exclude=cybermancy/.idea --exclude=cybermancy/pyCybermancy --exclude=cybermancy/src-descriptors cybermancy`

Create the cybermancy module .zip file excluding all the unnecessary folders.


