from wall_detection import image2birdview
from path_planning import path_planner
from voice import voice_class
import time
import cv2
import numpy as np
from realsense.rs_depth_util import depth_worker
from get_frame import get_frame
import sys
sys.path.append("./pointcloud/")
from pointcloud.get_pointcloud import get_pointcloud_frame
from pointcloud.pipeline_pc import pointcloud_pipeline
import argparse


def ModuleWrapper(args):
    
    # Parameters used by map builder
    num_row = args.row    # how many slices of the depth matrix
    num_col = args.col   # how many section to quantilize
    max_per_occ = 0.3 # percentage of 1s in a section to judge as occupied

    use_pointcloud = args.pointcloud
    use_bag = args.bagfile
    use_chebyshev = args.chebyshev
    show = args.verbose
    timing = args.time

    # Specify the depth matrix you want to use
    dep_mat_fn = 'wall_detection/samples/depth0009.npy'
    dep_mat_static = np.load(dep_mat_fn)

    # Instantiate a depth worker object to display depth matrix
    dw = depth_worker()
    #dw.show_depth_matrix(dep_mat_fn)

    # initialize the camera frame iterator
    if use_bag:
        img_gen = get_pointcloud_frame("./realsense/20181011_223353.bag")
    else:
        img_gen = get_frame()

    # instantiate an interface
    interface = voice_class.VoiceInterface(straight_file='voice/straight.mp3',
                                            turnleft_file = 'voice/turnleft.mp3',
                                            turnright_file = 'voice/turnright.mp3',
                                            hardleft_file = 'voice/hardleft.mp3',
                                            hardright_file = 'voice/hardright.mp3',
                                            STOP_file = 'voice/STOP.mp3',
                                            noway_file = 'voice/noway.mp3')

    # slice and quantilize the depth matrix
    squeeze = image2birdview.depth_bird_view()

    while(True):
        facing_wall = False
        target = None

        # fetch an image from camera
        dep_mat, pointcloud = next(img_gen)

        t_map_s = time.time()

        if not use_pointcloud:

            squeezed_matrix = squeeze.squeeze_matrix(dep_mat, num_slice=num_row)

            map_depth = squeeze.quantilize(squeezed_matrix, n_sec=num_col, max_per_occ=max_per_occ)
        else:

            #map_depth, target, facing_wall = pipeline(pointcloud, row = num_row, col = num_col, row_size = 6, col_size = 10, show=True)
            map_depth, target, facing_wall = pointcloud_pipeline(pointcloud, 
                                                            row_num = num_row, col_num = num_col, 
                                                            row_size = 6, col_size = 6, 
                                                            show=show, cheb=use_chebyshev)

        t_map_e = time.time()

        # perform path planning on the map
        t_plan_s = time.time()
        
        djikstra_planner = path_planner.path_planner(map_depth)
        djikstra_planner.gen_nodes()
        djikstra_planner.gen_paths()
        djikstra_planner.gen_buffer_mats()
        djikstra_planner.plan()

        t_plan_e = time.time()

        if target is None:
            target = djikstra_planner.find_default_target()
        if not facing_wall and target != None:
            if (djikstra_planner.check_target_valid(target)):
                path = djikstra_planner.find_optimal_path(target)
            else:
                path = []

            djikstra_planner.draw_path(path)
            dw.show_depth_matrix("", dep_mat)

            if timing:
                print("map time  " + str(t_map_e - t_map_s))
                print("plan time " + str(t_plan_e - t_plan_s))
                print("total time" + str(t_plan_e - t_map_s))

            cv2.waitKey(20)
            
            interface.play3(path,num_col)
        else:
            interface.play3([],num_col)
            print("no path")
        #quit()
        #input()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--bagfile", help="if use bagfile", default=False)
    parser.add_argument("-p", "--pointcloud", help="if use pointcloud", default=True)
    parser.add_argument("-v", "--verbose", help="display the points", default=False)
    parser.add_argument("-t", "--time", help="if timing the progra", default=False)
    parser.add_argument("-c", "--chebyshev", help="whteter use chebyshev", default=False)
    parser.add_argument("--row", help="number of rows in map", default=10)
    parser.add_argument("--col", help="number of columns in map", default=11)
    args = parser.parse_args()
    print(args.pointcloud)
    ModuleWrapper(args)
