#!/home/localadmin/myenv/bin/python3
'''Animates distances and measurment quality'''
from rplidar import RPLidar
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import signal
#linux port checking in terminal with: ls /dev/ttyUSB* or ls /dev/ttyACM*
PORT_NAME = '/dev/ttyUSB0'
DMAX = 6        #maximum distance in meters to display on the plot
IMIN = 0
IMAX = 50       #minimum and maximum intensity values for color mapping (adjust based on your LiDAR's output)

def update_line(num, iterator, line):
    scan = next(iterator)
    
    # Keep polar coordinates for circular display
    angles = []
    distances = []
    for meas in scan:
        angle_rad = np.radians(meas[1])
        distance_m = meas[2] / 1000
        angles.append(angle_rad)
        distances.append(distance_m)
    
    angles = np.array(angles)
    distances = np.array(distances)
    
    # Create custom colormap: red -> orange -> yellow -> lime (closer = more red)
    if len(distances) > 0:
        # Reverse normalization so closer distances = higher values = more red
        norm_distances = 1 - (distances / DMAX)
        norm_distances = np.clip(norm_distances, 0, 1)
        
        # Create custom colormap with specific colors (lime to red for reversed mapping)
        from matplotlib.colors import LinearSegmentedColormap
        colors = ['#00FF00', '#32CD32', '#FFFF00', '#FFA500', '#FF4500', '#FF0000']  # lime -> yellow -> orange -> red
        custom_cmap = LinearSegmentedColormap.from_list("lime_to_red", colors)
        
        colors = custom_cmap(norm_distances)
    else:
        colors = []
    
    # Update the scatter plot with polar coordinates
    if len(angles) > 0 and len(distances) > 0:
        points = np.column_stack((angles, distances))
        line.set_offsets(points)
        line.set_color(colors)
        line.set_sizes([5] * len(points))
    else:
        line.set_offsets(np.array([[0, 0]]))
    
    return line,

def close_figure(event):
    if event.key == 'c':
        plt.close(event.canvas.figure)

def _sigint_handler(signum, frame):
    print('\nCtrl-C received, closing figure')
    plt.close('all')


def run():
    global previous_scan
    signal.signal(signal.SIGINT, _sigint_handler)
    print("Starting LIDAR distance-based coloring...")
    try:
        lidar = RPLidar(PORT_NAME)
        print("LIDAR connected")
    except Exception as e:
        print(f"Failed to connect to LIDAR: {e}")
        return
    
    fig = plt.figure(figsize=(12, 12))  # larger figure size
    fig.canvas.mpl_connect('key_press_event', close_figure)
    ax = plt.subplot(111, projection='polar')  # Back to polar projection
    ax.set_theta_zero_location('N')     #sets the 0 degree angle to the top of the plot
    ax.set_theta_direction(-1)
    ax.set_facecolor("gray")     #sets the background color of the plot to gray
    line = ax.scatter([0, 0], [0, 0], s=5, c='lime', lw=0)       #initializes the scatter plot with green dots
    ax.set_rmax(DMAX)
    fig.patch.set_facecolor("gray")  #sets the background color of the plot to gray
    ax.grid(True, alpha=0.3)    
    for label in ax.get_yticklabels():      #makes the distance labels on the plot more transparent
        label.set_alpha(0.3)
    ax.set_title('LIDAR Distance-Based Coloring\n(Closer = Red, Farther = Lime)')
    
    # Add colorbar to show the distance scale
    from matplotlib.colors import LinearSegmentedColormap
    colors = ['#FF0000', '#FF4500', '#FFA500', '#FFFF00', '#32CD32', '#00FF00']
    custom_cmap = LinearSegmentedColormap.from_list("lime_to_red", colors)
    sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=plt.Normalize(vmin=0, vmax=DMAX))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.8, pad=0.1)
    cbar.set_label('Distance from LIDAR (meters)')
    cbar.set_ticks([0, 1, 2, 3, 4, 5, 6])
    cbar.set_ticklabels(['0m\n(red)', '1m', '2m\n(orange)', '3m', '4m\n(yellow)', '5m', '6m\n(lime)'])
    
    try:
        iterator = lidar.iter_scans()
        print("Starting animation... Press 'c' to stop")
        ani = animation.FuncAnimation(fig, update_line,     
            fargs=(iterator, line), interval=25, save_count=50)
        plt.show()
    except Exception as e:
        print(f"Animation error: {e}")
    finally:
        print("Cleaning up...")
        plt.close('all')
        try:
            lidar.stop()
            lidar.disconnect()
            print("LIDAR disconnected")
        except:
            pass

if __name__ == '__main__':
    run()