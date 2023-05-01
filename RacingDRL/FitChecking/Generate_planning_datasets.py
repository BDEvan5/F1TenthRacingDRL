import numpy as np
import os, glob
from matplotlib import pyplot as plt

from RacingDRL.Planners.TrackLine import TrackLine


set_n = 3
load_folder = f"Data/PurePursuitDataGen_{set_n}/"


N_BEAMS = 20
    
def calculate_inds(n_beams):
    inds = np.arange(0, 60, round(60/(n_beams-1)))
    if len(inds) < n_beams:
        inds = np.append(inds, 59)
    # print(f"inds: {inds} --> {n_beams} --> {len(inds)}")
    
    return inds

inds = calculate_inds(N_BEAMS)

def transform_waypoints(wpts, position, orientation):
    new_pts = wpts - position
    new_pts = new_pts @ np.array([[np.cos(orientation), -np.sin(orientation)], [np.sin(orientation), np.cos(orientation)]])
    
    return new_pts
    
def generate_fullPlanning_state(state, scan, track, n_wpts):
    relative_pts = generate_planning_waypoints(state, track, n_wpts)
    scaled_state = generate_motion_variables(state)
    scaled_scan = np.clip(scan[inds]/10, 0, 1)
    
    state = np.concatenate((scaled_scan, relative_pts, scaled_state))
    
    return state    

def generate_fullPlanning_state_rmMotion(state, scan, track, n_wpts):
    relative_pts = generate_planning_waypoints(state, track, n_wpts)
    scaled_scan = np.clip(scan[inds]/10, 0, 1)
    
    state = np.concatenate((scaled_scan, relative_pts))
    
    return state

def generate_fullPlanning_state_rmLidar(state, scan, track, n_wpts):
    relative_pts = generate_planning_waypoints(state, track, n_wpts)
    scaled_state = generate_motion_variables(state)
    
    state = np.concatenate((relative_pts, scaled_state))
    
    return state

def generate_planning_waypoints(state, track, n_wpts):
    idx, dists = track.get_trackline_segment(state[0:2])
        
    upcomings_inds = np.arange(idx, idx+n_wpts)
    if idx + n_wpts >= track.N:
        n_start_pts = idx + n_wpts - track.N
        upcomings_inds[n_wpts - n_start_pts:] = np.arange(0, n_start_pts)
        
    upcoming_pts = track.wpts[upcomings_inds]
    
    relative_pts = transform_waypoints(upcoming_pts, np.array([state[0:2]]), state[4])
    relative_pts = relative_pts / 2.5
    relative_pts = np.clip(relative_pts, 0, 1) #? ensures correct range
    
    return relative_pts.flatten()
    
def generate_motion_variables(state):
    speed = state[3] / 8
    anglular_vel = state[5] / 3.14
    steering_angle = state[2] / 0.4
    scaled_state = np.array([speed, anglular_vel, steering_angle])
    scaled_state = np.clip(scaled_state, -1, 1)
    
    return scaled_state

def generate_trajectoryTrack_state(state, _scan, track, n_wpts):
    idx, dists = track.get_trackline_segment(state[0:2])
        
    upcomings_inds = np.arange(idx, idx+n_wpts)
    if idx + n_wpts >= track.N:
        n_start_pts = idx + n_wpts - track.N
        upcomings_inds[n_wpts - n_start_pts:] = np.arange(0, n_start_pts)
        
    upcoming_pts = track.wpts[upcomings_inds]
    
    relative_pts = transform_waypoints(upcoming_pts, np.array([state[0:2]]), state[4])
    relative_pts = relative_pts / 2.5
    relative_pts = np.clip(relative_pts, 0, 1) #? ensures correct range
    
    #! There is no speed reference in the action....
    
    speed = state[3] / 8
    anglular_vel = state[5] / 3.14
    steering_angle = state[2] / 0.4
    scaled_state = np.array([speed, anglular_vel, steering_angle])
    scaled_state = np.clip(scaled_state, -1, 1)
    
    state = np.concatenate((relative_pts.flatten(), scaled_state))
    
    return state

def generate_fullTrajectoryTrack_state(state, _scan, track, n_wpts):
    idx, dists = track.get_trackline_segment(state[0:2])
        
    upcomings_inds = np.arange(idx, idx+n_wpts)
    if idx + n_wpts >= track.N:
        n_start_pts = idx + n_wpts - track.N
        upcomings_inds[n_wpts - n_start_pts:] = np.arange(0, n_start_pts)
        
    upcoming_pts = track.wpts[upcomings_inds]
    upcoming_speeds = track.vs[upcomings_inds] / 8
    
    relative_pts = transform_waypoints(upcoming_pts, np.array([state[0:2]]), state[4])
    relative_pts = relative_pts / 2.5
    relative_pts = np.clip(relative_pts, 0, 1) #? ensures correct range
    
    #! There is no speed reference in the action....
    
    speed = state[3] / 8
    anglular_vel = state[5] / 3.14
    steering_angle = state[2] / 0.4
    scaled_state = np.array([speed, anglular_vel, steering_angle])
    scaled_state = np.clip(scaled_state, -1, 1)
    
    state = np.concatenate((relative_pts.flatten(), scaled_state, upcoming_speeds))
    
    return state

    
    

def build_state_data_set(save_folder, data_tag, state_gen_fcn, n_waypoints, raceline=False):
    state_set = [] 
    
    for map_name in ["esp", "aut", "mco", "gbr"]:
        scan_data = np.load(load_folder + f"RawData/PurePursuit_{map_name}_DataGen_{set_n}_Lap_0_scans.npy")
        history_data = np.load(load_folder + f"RawData/PurePursuit_{map_name}_DataGen_{set_n}_Lap_0_history.npy")
        states = history_data[:, :7]

        track = TrackLine(map_name, raceline)
        prev_scans = np.zeros((2, scan_data[0].shape[0]))
        for i in range(len(states)):
            scaled_state = state_gen_fcn(states[i], scan_data[i], track, n_waypoints)
            state_set.append(scaled_state)
            prev_scans = np.roll(prev_scans, 1, axis=0)
            prev_scans[0] = scan_data[i]
            
    
    state_set = np.array(state_set)
    if not os.path.exists(save_folder + f"DataSets/"): os.mkdir(save_folder + f"DataSets/")
    np.save(save_folder + f"DataSets/PurePursuit_{data_tag}_states.npy", state_set)

    print(f"StateShape: {state_set.shape} ")
    print(f"State Minimum: {np.amin(state_set, axis=0)}")
    print(f"State Maximum: {np.amax(state_set, axis=0)}")
    

def build_action_data_set(save_folder):
    normal_action = np.array([0.4, 8])
    
    action_set = []
    for map_name in ["esp", "aut", "mco", "gbr"]:
        history_data = np.load(load_folder + f"RawData/PurePursuit_{map_name}_DataGen_{set_n}_Lap_0_history.npy")
        actions = history_data[:, 7:]

        action_set.append(actions / normal_action)
        
    action_set = np.concatenate(action_set, axis=0)
            
    if not os.path.exists(save_folder + f"DataSets/"): os.mkdir(save_folder + f"DataSets/")
    np.save(save_folder + "DataSets/PurePursuit_actions.npy", action_set)

    print(f"ActionShape: {action_set.shape}")
    print(f"Action: ({np.amin(action_set, axis=0)}, {np.amax(action_set, axis=0)})")
    


def build_trajectoryTrack_nWaypoints():
    experiment_name = "trajectoryTrack_nWaypoints"
    save_folder = f"NetworkFitting/{experiment_name}_{set_n}/"

    if not os.path.exists(save_folder):
        os.mkdir(save_folder)

    build_action_data_set(save_folder)

    inds = [0, 1, 2, 4, 6, 8, 10, 12, 15, 20]
    for i in inds:
        build_state_data_set(save_folder, f"trajectoryTrack_{i}", generate_trajectoryTrack_state, i, True)



def build_fullPlanning_ablation():
    experiment_name = "fullPlanning_ablation"
    save_folder = f"NetworkFitting/{experiment_name}_{set_n}/"

    if not os.path.exists(save_folder):
        os.mkdir(save_folder)

    build_action_data_set(save_folder)

    build_state_data_set(save_folder, f"fullPlanning_full", generate_fullPlanning_state, 10, False)
    build_state_data_set(save_folder, f"fullPlanning_rmMotion", generate_fullPlanning_state_rmMotion, 10, False)
    build_state_data_set(save_folder, f"fullPlanning_rmLidar", generate_fullPlanning_state_rmLidar, 10, False)
    build_state_data_set(save_folder, f"fullPlanning_rmWaypoints", generate_fullPlanning_state, 0, False)
    build_state_data_set(save_folder, f"fullPlanning_Motion", generate_fullPlanning_state_rmLidar, 0, False)

def build_comparison_data_set():
    experiment_name = "comparison"
    save_folder = f"NetworkFitting/{experiment_name}_{set_n}/"

    if not os.path.exists(save_folder):
        os.mkdir(save_folder)

    build_action_data_set(save_folder)

    build_state_data_set(save_folder, f"fullPlanning", generate_fullPlanning_state, 10, False)
    build_state_data_set(save_folder, f"trajectoryTrack", generate_trajectoryTrack_state, 10, True)
    
    
    
if __name__ == "__main__":
    # build_trajectoryTrack_nWaypoints()
    # build_fullPlanning_ablation()
    
    build_comparison_data_set()