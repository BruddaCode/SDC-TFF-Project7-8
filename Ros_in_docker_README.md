# Guide to running ROS2 in Docker

## 1. Install docker
 - Linux --> https://docs.docker.com/engine/install/

Volg de installatie instructies

## 2. Open terminal
To open a terminal press `CTRL + Alt + T`

All terminal commands will happend in the same terminal unless otherwise specified.

## 3. Create a workspace
This is where the ROS2 code will live.

In the terminal type:

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
```

## 4. Creating a Dockerfile

In the terminal type:
```bash
nano Dockerfile
```
Past the following in the terminal.

```Dockerfile        
FROM osrf/ros:jazzy-desktop

# Install deps
RUN apt update && apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-jazzy-demo-nodes-cpp \
    ros-jazzy-demo-nodes-py \
    && rm -rf /var/lib/apt/lists/*

# Set workspace
    WORKDIR /ros2_ws
    COPY ./src ./src

# Build your code
    RUN . /opt/ros/jazzy/setup.sh && \
    rosdep update && rosdep install --from-paths src --ignore-src -r -y && \
    colcon build

# Default launch command
    ENTRYPOINT ["/bin/bash"]
```
To save and close the file you do the following:
- in nano: 
    - press `CTRL + 0` -> `Enter` -> `CTRL + x`

## 5. Building the Docker image
In the terminal type:

```bash
docker build -t my_ros2_app .
```

## 6. Running the ROS2 container
Once the building of the image is finished, run the following:
```bash
docker run -it --name ros2_container my_ros2_app
```
After this command the terminal will change slightly. 
This means that you are inside the Docker box.

## 7. Using ROS2 inside the container
First we need to source ROS inside the container to do that type the following in the terminal:
```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

## 8. Checking the ROS2 application
To make sure ROS2 is running correctly enter the following in the terminal:
```bash
ros2 run demo_nodes_cpp talker
```
Open a second terminal and type the following:
```bash
docker exec -it ros2_container bash
source /opt/ros/jazzy/setup.bash
ros2 run demo_nodes_cpp listener
```
If the second terminal receives messages then ROS2 is working.

Now press `CTRL + c` in both terminals

# Working out of VS code - Live editing

## 1. Stop the current container
#### 1. Open a terminal and enter the following:
```bash
docker stop ros2_container
```
If it says “not running”, that’s fine.

#### 2. Remove any old containers

Enter the following into the terminal:
```bash
docker rm ros2_container
```

## 2. Running the container
To run the container with a workspace mounted type the following it the terminal:
```bash
docker run -it \
    -v ~/ros2_ws:/ros2_ws \
    --name ros2_container \
    my_ros2_app
```
***IMPORTANT*** Leave this terminal running, DO NOT CLOSE

## 3. VS code

#### Install extentions
1. Open VS code
2. Press `CTRL + Shift + X`
3. Search for Dev Containers (by microsoft)
4. Click install

## 4. Attaching VS code to the container
Inside VS code do the following:
1. Press `CTRL + Shift + P`
2. Type in the bar: **Dev Containers: Attach to Running Container**
3. Select: **ROS2_container**

VS code will open in a **new window** which is now *inside* the container

4. Go to **file** -> **Open folder**
5. In the bar type `/ros2_ws`
6. Press OK

You should now see in the file explorer a Dockerfile and a src folder.

## 5. Building and running ROS2 in VS code
#### 1. Terminal
Open the terminal *inside* VS code  
Menu: **Terminal -> New Terminal**  
You should see:

```code
root@containerID:/ros2_ws# 
```
Run the following commands in the VS code terminal unless otherwise specified.
#### 2. Source ROS2
Source ROS2:
```bash
source /opt/ros/jazzy/setup.bash
 ```
If you've already built your workspace:
```bash
source install/setup.bash
```
#### 3. Build the workspace
```bash
colcon build
```
#### 4. Test run the nodes  
In one terminal run:
```bash
ros2 run demo_nodes_cpp talker
```
In a second terminal, after following step 2, run:
```bash
ros2 run demo_nodes_cpp listener
```
If the second one receives messages then it's working!

#### 5. Confirming live editing works
Open a host terminal and run:
```bash
touch ~/ros2_ws/src/text.txt
```
On the terminal in VS code run:
```bash
ls /ros2_ws/src
```
If you see text.txt, live editing is working.

## Daily workflow
#### 1. start container (host terminal)
Open a host terminal and run:
```bash 
docker start ros2_container
```
You can check if its running by:
```bash
docker ps
```
You should see ros2_container in that list.

#### 2. Attach VS code
1. Open VS code
2. press `CTRL + Shift + P`
Then:
3. Type: **Dev Containers: Attach to Running Container**
4. Select: **ros2_container**
VS code should then open an **new window** which is insde the container

#### 3. Open the workspace (If nessesary)
VS code should open the new window with the correct folder if you've opened it before.
Should this not be the case then do the following:  
In the new window:
1. Go to **File -> Open Folder**
2. Enter:
```text
/ros2_ws
```
3. Click **OK**

#### 4. Open container terminal
In the same VS code window:
- Go to **Terminal -> New Terminal**
You should now see something like this in the terminal:
```text
root@containerID:/ros2_ws#
```
This terminal runs *inside* the container.

#### 5. Source ROS2 
In the first new VS code terminal run:
```bash 
source /opt/ros/jazzy/setup.bash
```
If you've already built your workspace before, run:
```bash
source install/setup.bash
```
You'll repeat this in every new terminal you open in VS code.

#### 6. Editing code
You can now browse `/src` in the VS code explorer.

However when you change code you need to do the following in the VS terminal:
```bash
cd /ros2_ws
colcon build
```
After the build is successful:
```bash
source install/setup.bash
```

#### 7. running ROS2 nodes
In the VS terminal, run:
```bash
ros2 run <package_name> <node_executable>
#example
ros2 run demo_nodes_cpp talker
```
If you need a second node:
1. Open another terminal in VS code: **Terminal -> New Terminal**
2. Again: 
```bash 
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run demo_nodes_cpp listener
```
Now you are running multiple nodes inside the same container

#### 8. Stopping nodes / finish work
- To stop running a node press `CTRL + C` in that terminal
- To close VS just close the window
- To stop the container:  
    In the host terminal:
    ```bash
    docker stop ros2_container
    ```
