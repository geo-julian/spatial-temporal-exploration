import requests, os, glob, errno
from netCDF4 import Dataset
from matplotlib.colors import LinearSegmentedColormap
import scipy.spatial
import pandas as pd
import cv2
from parameters import parameters as params

def get_age_grid_color_map_from_cpt(cpt_file):
    values=[]
    colors=[]
    with open(cpt_file,'r') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line[0] in ['#', 'B', 'F', 'N']: continue
            vals = line.split()
            if len(vals) !=8: continue
            values.append(float(vals[0]))
            values.append(float(vals[4]))
            colors.append([float(vals[1]),float(vals[2]),float(vals[3])])
            colors.append([float(vals[5]),float(vals[6]),float(vals[7])])

    colour_list= []
    for i in range(len(values)):
        colour_list.append((values[i]/(values[-1]-values[0]), 
                        [x/255.0 for x in colors[i]]))
    return LinearSegmentedColormap.from_list('agegrid_cmap', colour_list)

import pygplates
import numpy as np

def make_GPML_velocity_feature(Long,Lat):
# function to make a velocity mesh nodes at an arbitrary set of points defined in Lat
# Long and Lat are assumed to be 1d arrays. 

    # Add points to a multipoint geometry
    multi_point = pygplates.MultiPointOnSphere([(float(lat),float(lon)) for lat, lon in zip(Lat,Long)])

    # Create a feature containing the multipoint feature, and defined as MeshNode type
    meshnode_feature = pygplates.Feature(pygplates.FeatureType.create_from_qualified_string('gpml:MeshNode'))
    meshnode_feature.set_geometry(multi_point)
    meshnode_feature.set_name('Velocity Mesh Nodes from pygplates')

    output_feature_collection = pygplates.FeatureCollection(meshnode_feature)
    
    # NB: at this point, the feature could be written to a file using
    # output_feature_collection.write('myfilename.gpmlz')
    
    # for use within the notebook, the velocity domain feature is returned from the function
    return output_feature_collection


def Get_Plate_Velocities(velocity_domain_features, topology_features, rotation_model, time, delta_time, rep='vector_comp'):
    # All domain points and associated (magnitude, azimuth, inclination) velocities for the current time.
    all_domain_points = []
    all_velocities = []

    # Partition our velocity domain features into our topological plate polygons at the current 'time'.
    plate_partitioner = pygplates.PlatePartitioner(topology_features, rotation_model, time)

    for velocity_domain_feature in velocity_domain_features:

        # A velocity domain feature usually has a single geometry but we'll assume it can be any number.
        # Iterate over them all.
        for velocity_domain_geometry in velocity_domain_feature.get_geometries():

            for velocity_domain_point in velocity_domain_geometry.get_points():

                all_domain_points.append(velocity_domain_point)

                partitioning_plate = plate_partitioner.partition_point(velocity_domain_point)
                if partitioning_plate:

                    # We need the newly assigned plate ID to get the equivalent stage rotation of that tectonic plate.
                    partitioning_plate_id = partitioning_plate.get_feature().get_reconstruction_plate_id()

                    # Get the stage rotation of partitioning plate from 'time + delta_time' to 'time'.
                    equivalent_stage_rotation = rotation_model.get_rotation(time, partitioning_plate_id, time + delta_time)

                    # Calculate velocity at the velocity domain point.
                    # This is from 'time + delta_time' to 'time' on the partitioning plate.
                    velocity_vectors = pygplates.calculate_velocities(
                        [velocity_domain_point],
                        equivalent_stage_rotation,
                        delta_time)
                    
                    if rep=='mag_azim':
                        # Convert global 3D velocity vectors to local (magnitude, azimuth, inclination) tuples (one tuple per point).
                        velocities = pygplates.LocalCartesian.convert_from_geocentric_to_magnitude_azimuth_inclination(
                            [velocity_domain_point],
                            velocity_vectors)
                        all_velocities.append(velocities[0])

                    elif rep=='vector_comp':
                        # Convert global 3D velocity vectors to local (magnitude, azimuth, inclination) tuples (one tuple per point).
                        velocities = pygplates.LocalCartesian.convert_from_geocentric_to_north_east_down(
                                [velocity_domain_point],
                                velocity_vectors)
                        all_velocities.append(velocities[0])

                else:
                    all_velocities.append((0,0,0))

    return all_velocities

def get_velocity_x_y_u_v(time,rotation_model,topology_filenames):
    delta_time = 5.
    Xnodes = np.arange(-180,180,10)
    Ynodes = np.arange(-90,90,10)
    Xg,Yg = np.meshgrid(Xnodes,Ynodes)
    Xg = Xg.flatten()
    Yg = Yg.flatten()
    velocity_domain_features = make_GPML_velocity_feature(Xg,Yg)

    # Load the topological plate polygon features.
    topology_features = []
    for fname in topology_filenames:
        for f in pygplates.FeatureCollection(fname):
            topology_features.append(f)


    # Call the function we created above to get the velocities
    all_velocities = Get_Plate_Velocities(velocity_domain_features,
                                          topology_features,
                                          rotation_model,
                                          time,
                                          delta_time,
                                          'vector_comp')

    uu=[]
    vv=[]
    for vel in all_velocities:
        if not hasattr(vel, 'get_y'): 
            uu.append(vel[1])
            vv.append(vel[0])
        else:
            uu.append(vel.get_y())
            vv.append(vel.get_x())
    u = np.asarray([uu]).reshape((Ynodes.shape[0],Xnodes.shape[0]))
    v = np.asarray([vv]).reshape((Ynodes.shape[0],Xnodes.shape[0]))

    return Xnodes, Ynodes, u, v
    # compute native x,y coordinates of grid.
    #x, y = m(Xg, Yg)

    #uproj,vproj,xx,yy = m.transform_vector(u,v,Xnodes,Ynodes,15,15,returnxy=True,masked=True)
    # now plot.
    #Q = m.quiver(xx,yy,uproj,vproj,scale=1000,color='grey')
    # make quiver key.
    #qk = plt.quiverkey(Q, 0.95, 1.05, 50, '50 mm/yr', labelpos='W')
    
def get_subduction_teeth(lons, lats, tesselation_degrees=5, triangle_base_length=3, triangle_aspect=-1):
    distance = tesselation_degrees 
    teeth=[]
    PA = np.array([lons[0], lats[0]])
    for lon, lat in zip(lons[1:], lats[1:]):
        PB = np.array([lon, lat])
        AB_dist = np.sqrt((PB[0]-PA[0])**2 + (PB[1]-PA[1])**2)
        distance += AB_dist
        if distance > tesselation_degrees:
            distance = 0
            AB_norm = (PB - PA)/AB_dist
            AB_perpendicular = np.array([AB_norm[1], -AB_norm[0]]) # perpendicular to line A->B
            B0 = PA + triangle_base_length*AB_norm #new B
            C0 = PA + 0.5*triangle_base_length*AB_norm #middle point between A and B
            # project point along normal vector
            C = C0 + triangle_base_length*triangle_aspect*AB_perpendicular
            teeth.append([PA,B0,C])#three vertices of the triagle

        PA = PB
    return teeth

def get_subduction_geometries(subduction_geoms, shared_boundary_sections):
    for shared_boundary_section in shared_boundary_sections:
        if shared_boundary_section.get_feature().get_feature_type() != pygplates.FeatureType.gpml_subduction_zone:
                continue
        for shared_sub_segment in shared_boundary_section.get_shared_sub_segments():
            subduction_polarity = shared_sub_segment.get_feature().get_enumeration(pygplates.PropertyName.gpml_subduction_polarity)
            if subduction_polarity == "Left":
                subduction_geoms.append((shared_sub_segment.get_resolved_geometry(),-1))
            else:
                subduction_geoms.append((shared_sub_segment.get_resolved_geometry(),1))
    return 

def download_agegrid(time):
    if not os.path.isdir('./AgeGrids'):
        os.system('mkdir AgeGrids')

    # download the age grid if necessary
    url_temp='https://www.earthbyte.org/webdav/ftp/Data_Collections/Muller_etal_2016_AREPS/Muller_etal_2016_AREPS_Agegrids/Muller_etal_2016_AREPS_Agegrids_v1.15/netCDF-4_0-230Ma/EarthByte_AREPS_v1.15_Muller_etal_2016_AgeGrid-{}.nc'
    file_temp='./AgeGrids/EarthByte_AREPS_v1.15_Muller_etal_2016_AgeGrid-{}.nc'
    agegrid_file = file_temp.format(time)
    if not os.path.isfile(agegrid_file):
        print('Downloading age grids...')
        myfile = requests.get(url_temp.format(time))
        open(agegrid_file, 'wb').write(myfile.content)
    return agegrid_file

import numpy as np
import math

def plate_isotherm_depth(age, temp, *vartuple) :
    "Computes the depth to the temp - isotherm in a cooling plate mode.\
    Solution by iteration. By default the plate thickness is 125 km as\
    in Parsons/Sclater.  Change given a 3rd parameter."

    if len(vartuple) != 0 :
        PLATE_THICKNESS_KM = vartuple[0]
    else :
        PLATE_THICKNESS_KM = 125

    PLATE_THICKNESS = PLATE_THICKNESS_KM * 1000
    
    
    # default depth is 0
    z = 0

    if age <= 0.0 :
        z_try = 0
        done = 1
    else :
        z_too_small = 0.0
        z_too_big = PLATE_THICKNESS
        done = 0
        n_try = 0
            
    while done != 1 and n_try < 20 :
        n_try += 1
        z_try = 0.5 * (z_too_small + z_too_big)
        t_try = plate_temp (age, z_try, PLATE_THICKNESS)
        t_wrong = temp - t_try

        if t_wrong < -0.001 :
            z_too_big = z_try
        elif t_wrong > 0.001 :
            z_too_small = z_try
        else :
            done = 1

        z = z_try
    return z

def plate_temp(age, z, PLATE_THICKNESS) :
    "Computes the temperature in a cooling plate for age = t\
    and at a depth = z."

    KAPPA = 0.804E-6
    T_MANTLE = 1350.0
    T_SURFACE = 0.0
    SEC_PR_MY = 3.15576e13

    t = T_SURFACE

    sum = 0
    sine_arg = math.pi * z / PLATE_THICKNESS
    exp_arg = -KAPPA * math.pi * math.pi * age * SEC_PR_MY / (PLATE_THICKNESS * PLATE_THICKNESS)
    for k in range(1, 20) :
        sum = sum + np.sin(k * sine_arg) * np.exp(k*k*exp_arg)/k

    if age <= 0.0 :
        t = T_MANTLE * np.ones(z.shape)
    else :
        t = t + 2.0 * sum * (T_MANTLE - T_SURFACE)/math.pi + (T_MANTLE - T_SURFACE) * z/PLATE_THICKNESS
    
    return t

# input: degrees between two points on sphere
# output: straight distance between the two points (assume the earth radius is 1)
# to get the kilometers, use the return value to multiply by the real earth radius
def degree_to_straight_distance(degree):
    return math.sin(math.radians(degree)) / math.sin(math.radians(90 - degree/2.))


def select_points_in_region(candidate_lons, candidate_lats, trench_lons, trech_lats, region=5):
    #build the tree
    points_3d = [pygplates.PointOnSphere((lat,lon)).to_xyz() for lon, lat in zip(trench_lons, trech_lats)]
    points_tree = scipy.spatial.cKDTree(points_3d)

    candidates = [pygplates.PointOnSphere((lat,lon)).to_xyz() for lon, lat in zip(candidate_lons, candidate_lats)]
    
    dists, indices = points_tree.query(
                candidates, k=1, distance_upper_bound=degree_to_straight_distance(region))

    return indices<len(points_3d)

def query_raster(raster_name, lons, lats):
    #construct the grid tree
    grid_x, grid_y = np.mgrid[-90:91, -180:181]
    grid_points = [pygplates.PointOnSphere((float(row[0]), float(row[1]))).to_xyz() for row in zip(grid_x.flatten(), grid_y.flatten())]

    rasterfile = Dataset(raster_name,'r')
    z = rasterfile.variables['z'][:] #masked array
    zz = cv2.resize(z, dsize=(361, 181), interpolation=cv2.INTER_CUBIC)
    zz = np.roll(zz,180)
    z = np.ma.asarray(zz.flatten())
    
    grid_points = np.asarray(grid_points)
    z_idx = ~np.isnan(z)
    z = z[z_idx]
    grid_tree = scipy.spatial.cKDTree(grid_points[z_idx])
    
    points=[pygplates.PointOnSphere((float(row[1]), float(row[0]))).to_xyz() for row in zip(lons, lats)]
    
    # query the tree 
    dists, indices = grid_tree.query(points, k=1) 
    return z[indices]

def print_columns():
    columns = [
        'reconstructed mineral deposits longitude',
        'reconstructed mineral deposits latitude',
        'distance to the nearest trench point',
        'the index of trench point',
        'trench point longitude',
        'trench point latitude',
        'subducting convergence (relative to trench) velocity magnitude (in cm/yr)',
        'subducting convergence velocity obliquity angle (angle between trench normal vector and convergence velocity vector)',
        'trench absolute (relative to anchor plate) velocity magnitude (in cm/yr)',
        'trench absolute velocity obliquity angle (angle between trench normal vector and trench absolute velocity vector)',
        'length of arc segment (in degrees) that current point is on',
        'trench normal azimuth angle (clockwise starting at North, ie, 0 to 360 degrees) at current point',
        'subducting plate ID',
        'trench plate ID',
        'distance (in degrees) along the trench line to the nearest trench edge',
        'the distance (in degrees) along the trench line from the start edge of the trench',
        'convergence velocity orthogonal (in cm/yr)',
        'convergence velocity parallel (in cm/yr)',
        'the trench plate absolute velocity orthogonal (in cm/yr)',
        'the trench plate absolute velocity parallel (in cm/yr)',
        'the subducting plate absolute velocity magnitude (in cm/yr)',
        'the subducting plate absolute velocity obliquity angle (in degrees)',
        'the subducting plate absolute velocity orthogonal',
        'the subducting plate absolute velocity parallel',
        'sea floor age',
        'subduction volume(km3y)', 
        'decompacted sediment thickness', 
        'sediment thickness', 
        'ocean crust carb percent'
      ]
    for i in range(len(columns)):
        print('*', i, columns[i])

# expand *.rot, *.gpml
def get_files(names):
    files=[]
    for f in names:
        files += glob.glob(f)
    return files

#
def get_trench_points(age, top_left_lon=None, top_left_lat=None,
                      bottom_right_lon=None, bottom_right_lat=None):
    conv_dir = params['convergence_data_dir']
    conv_prefix = params['convergence_data_filename_prefix']
    conv_ext = params['convergence_data_filename_ext']
    
    fn = conv_dir + conv_prefix + f'_{age:.2f}.' + conv_ext
    
    if not os.path.isfile(fn):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), fn)
        
    data = pd.read_csv(fn)
    
    if [top_left_lon, top_left_lat, bottom_right_lon, bottom_right_lat].count(None) == 0:
        data = data[data['trench_lon']>top_left_lon]
        data = data[data['trench_lon']<bottom_right_lon]
        data = data[data['trench_lat']>bottom_right_lat]
        data = data[data['trench_lat']<top_left_lat]
    return data


