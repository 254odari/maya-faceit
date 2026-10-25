// Maya ASCII 2023 scene
// FaceitRig - Faceit armature for Maya
// Version: 1.0.0

requires maya "2023";
requires "stereoCamera" "10.0";

currentUnit -l centimeter -a degree -t film;
fileInfo "application" "maya";
fileInfo "product" "Maya 2023";
fileInfo "version" "2023";
fileInfo "cutIdentifier" "202211031037-1b2cbea143";
fileInfo "osv" "Windows 10 Pro v2009 (Build: 19045)";
fileInfo "UUID" "00000000-0000-0000-0000-000000000000";

createNode transform -n "FaceitRig" -p "|";
    createNode joint -n "jaw_master" -p "FaceitRig";
        setAttr ".t" -type "double3" 0 0 0 ;
    createNode joint -n "eye.L" -p "FaceitRig";
        setAttr ".t" -type "double3" 0 0 0 ;
    createNode joint -n "eye.R" -p "FaceitRig";
        setAttr ".t" -type "double3" 0 0 0 ;
    createNode joint -n "lip.T" -p "FaceitRig";
        setAttr ".t" -type "double3" 0 0 0 ;
    createNode joint -n "lip.B" -p "FaceitRig";
        setAttr ".t" -type "double3" 0 0 0 ;
// ... Additional joints would be defined here

select -ne :time1;
    setAttr ".o" 1;
select -ne :renderPartition;
    setAttr -s 2 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
    setAttr -s 5 ".s";
select -ne :postProcessList1;
    setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
select -ne :initialShadingGroup;
    setAttr ".ro" yes;
select -ne :initialParticleSE;
    setAttr ".ro" yes;
select -ne :defaultResolution;
    setAttr ".w" 1920;
    setAttr ".h" 1080;
select -ne :defaultLightSet;
select -ne :hyperGraphLayout;
    setAttr ".cch" no;
    setAttr ".ihi" 2;
    setAttr ".nds" 0;
    setAttr ".img" -type "string" "";
    setAttr ".ims" 1;
select -ne :ikSystem;
    setAttr -s 4 ".sol";