from wall_detection import image2birdview
from path_planning import path_planner
from voice import voice_class
import time
import numpy as np
from realsense.rs_depth_util import *
import sys
sys.path.append("./tinyYOLOv2/")
from tinyYOLOv2.get_frame_bag import *
from tinyYOLOv2.door_coord import find_door
from tinyYOLOv2 import obj_det
from postprocess import fuzzyfilter_detect
import argparse

use_tensor = True
Use_bag_file = False

class ModuleWrapper(object):

    def __init__(self):
        
        # Parameters used by map builder
        num_slice = 10    # how many slices of the depth matrix
        nun_section = 7   # how many section to quantilize
        max_per_occ = 0.3 # percentage of 1s in a section to judge as occupied

        # Specify the depth matrix you want to use
        #dep_mat_fn = 'wall_detection/samples/depth0009.npy'
        #dep_mat = np.load(dep_mat_fn)

        # Instantiate a depth worker object to display depth matrix
        #dw = depth_worker()
        #dw.show_depth_matrix(dep_mat_fn)

        # initialize the camera frame iterator
        img_gen = get_frame(Use_bag_file)

        f = fuzzyfilter_detect.FuzzyFilter( 5.25, 10, 7, 0.5, 3)

        if use_tensor:
            t = obj_det.obj_det()
        # instantiate an interface
        interface = voice_class.VoiceInterface(straight_file='voice/straight.mp3',
                                               turnleft_file = 'voice/turnleft.mp3',
                                                turnright_file = 'voice/turnright.mp3',
                                                hardleft_file = 'voice/hardleft.mp3',
                                                hardright_file = 'voice/hardright.mp3',
                                                STOP_file = 'voice/STOP.mp3',
                                                noway_file = 'voice/noway.mp3')

        while(True):
            # fetch an image from camera
            dep_mat, color_mat = next(img_gen)

            # slice and quantilize the depth matrix
            self.squeeze = image2birdview.depth_bird_view()

            t_sq_s = time.time()
            squeezed_matrix = self.squeeze.squeeze_matrix(dep_mat, num_slice=num_slice)
            t_sq_e = time.time()

            t_qu_s = time.time()
            map_depth = self.squeeze.quantilize(squeezed_matrix, n_sec=nun_section, max_per_occ=max_per_occ)
            t_qu_e = time.time()

            if use_tensor:
                coord = t.detect_frame(color_mat,use_bag = Use_bag_file)
            
            target_door = []

            if use_tensor:
                # find the coordinate in map with depth matrix and bounding box
                if(len(coord)!=0):
                    target_door, img_coord = find_door( dep_mat, coord)
                    cv2.rectangle(color_mat,(img_coord[0],img_coord[2]),(img_coord[1],img_coord[3]),(0,255,0),3)
                    print(target_door)
                    if(target_door[0]>9):
                        target_door[0]=9
                    map_depth[target_door[0], target_door[1]] = 0

            #cv2.imshow( "Display window", color_mat)
            
            # perform path planning on the map
            t_plan_s = time.time()
            print(map_depth)
            p = path_planner.path_planner(map_depth)
            p.gen_nodes()   # path planner initializetion
            p.gen_paths()   # path planner initializetion
            p.gen_buffer_mats() # path planner initializetion
            p.plan()        # path planner planning

            print("target door is ",target_door)

            if target_door is not None and len(target_door) != 0:
                target = target_door
            else:
                target = p.find_default_target(0)

            if len(target) > 0:
                path = p.find_optimal_path(target)
                t_plan_e = time.time()
                p.draw_path(path)
                print("squeeze time " + str(t_sq_e - t_sq_s))
                print("quantilize time " + str(t_qu_e - t_qu_s))
                print("plan time" + str(t_plan_e - t_plan_s))

                cv2.waitKey(200)
                print(path)

                print("Filter ",f.update(path))

                interface.play4(path,nun_section)
            else:
                #interface.play1([],nun_section)
                print("no path")
            #input()

if __name__ == "__main__":

    m = ModuleWrapper()
