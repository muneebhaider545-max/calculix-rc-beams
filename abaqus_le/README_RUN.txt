C25-CFRP reduced 3D Abaqus Learning Edition run package

1. Install Abaqus Learning Edition on Windows.
2. Extract this ZIP into a writable folder such as C:\AbaqusJobs\C25_CFRP.
3. Double-click RUN_ABAQUS_LE.bat.
4. The batch file first performs an Abaqus syntax check, then runs Abaqus/Standard.
5. On successful completion it automatically extracts:
   - load-deflection history to C25_CFRP_Abaqus_LE_reduced3D_history.csv
   - peak-load/damage summary to C25_CFRP_Abaqus_LE_reduced3D_summary.txt
   - native Abaqus result database C25_CFRP_Abaqus_LE_reduced3D.odb

If automatic command detection fails, launch the Abaqus Learning Edition Command window,
change directory to this folder, and run RUN_ABAQUS_LE.bat.

Scientific note:
The beam dimensions, measured concrete strength, CFRP dimensions/modulus and experimental
loads are source-backed. CDP post-peak laws and cohesive-interface parameters are initial
calibration assumptions because the source experiment did not report the required constitutive
interface tests. Do not describe the numerical result as independently predictive until calibration
and validation checks are completed.
