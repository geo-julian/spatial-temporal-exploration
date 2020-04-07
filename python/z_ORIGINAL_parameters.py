
parameters = {
    #IMPORTANT: the convergence.py depends on the PlateTectonicTools, 
    #you need to tell the script where to find it
    #You can clone the code repository here https://github.com/EarthByte/PlateTectonicTools.git
    "plate_tectonic_tools_path" : "../../PlateTectonicTools/ptt/",
    
    #the file which contains the seed points.
    #coregistration input file 
    'input_file' : 'coregistration_input_data_example_155.csv',
    
    #folder contains the coregistration output files.
    'output_dir' : 'coreg_output',
    
    "time" : {
        "start" : 0,
        "end"   : 230,
        "step"  : 1
    },
    #the region of interest parameters are used in coregistration.py
    #given a seed point, the coregistration code looks for the nearest geomery within region[0] first
    #if not found, continue to search in region[1], region[2], etc
    #if still not found after having tried all regions, give up
    #the distance is in degrees. 
    "regions" : [5, 10],
    
    "rotation_files" : ["../data/Global_EarthByte_230-0Ma_GK07_AREPS.rot"],
    "topology_files" : ["../data/Global_EarthByte_230-0Ma_GK07_AREPS_PlateBoundaries.gpml.gz",  
            "../data/Global_EarthByte_230-0Ma_GK07_AREPS_Topology_BuildingBlocks.gpml.gz"],
    
    #the following two parameters are used by subduction_convergence
    #see https://github.com/EarthByte/PlateTectonicTools/blob/master/ptt/subduction_convergence.py
    "threshold_sampling_distance_degrees" : 0.2,
    "velocity_delta_time" : 1,
    
    #a list of file paths from which the coregistration scripts query data
    "vector_files" : [
        './convergence_data/subStats_{time:.2f}.csv', #can be generated by convergence.py
        #'./convergence_data_1/subStats_{time:.2f}.csv',
        #more files below
    ],
    
    "anchor_plate_id" : 0, #see https://www.gplates.org/user-manual/MoreReconstructions.html
    
    #a list of grid files from which the coregistration scripts query data
    "grid_files" : [
        #'./AgeGrids/EarthByte_AREPS_v1.15_Muller_etal_2016_AgeGrid-{time:d}.nc',
        #'../data/carbonate_sed_thickness/decompacted_sediment_thickness_0.5_{time:d}.nc',
        #'../data/predicted_oceanic_sediment_thickness/sed_thick_0.2d_{time:d}.nc',
        #'../data/ocean_crust_CO2_grids/ocean_crust_carb_percent_{time:d}.nc'
        #can be downloaded from
        #https://www.earthbyte.org/webdav/ftp/Data_Collections/Muller_etal_2016_AREPS/               
        #Muller_etal_2016_AREPS_Agegrids/Muller_etal_2016_AREPS_Agegrids_v1.15/netCDF-4_0-230Ma/ 
        #,
        #'../data/AgeGrids_1/EarthByte_AREPS_v1.15_Muller_etal_2016_AgeGrid-{time:d}.nc' 
        #more grid files below...
    ],
    
    "convergence_data_filename_prefix" : "subStats",
    "convergence_data_filename_ext" : "csv",
    "convergence_data_dir" : "./convergence_data/",
}