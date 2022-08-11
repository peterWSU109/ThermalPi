# Thermal Pi Project
The Thermal Pi project repository contains the code and schematics to create a contactless, human body temperature screening device with a Raspberry Pi. This prototype was created as a Senior design project at Wichita State University in Spring 2022 by Peter M., Lexi W., Shaima H., and Adrian S.


![image](https://user-images.githubusercontent.com/99409502/183681615-91228a1e-6a97-4f3c-8c00-d679fa8c1665.png)
![image](https://user-images.githubusercontent.com/99409502/183681972-60288032-311e-4323-a0b5-ae1a2fa4eb10.png)
![image](https://user-images.githubusercontent.com/99409502/183682458-b8451d3c-55b2-4d2e-822c-af865bdd11c3.png)

See video for basic demonstration [Video_demonstration](https://youtu.be/Jvymuu6-stE)


## Design Goals/Specifications

1) Small (Able to be held with one hand), and lightweight (Met!)
2) Screen people at a distance 3 to 6 feet (Met!)
3) Complete screening in less than 3 seconds (Met!)
4) Create friendly UI for the end user (Met!)
5) Stretch Goal - Measure multiple users at once (Met!)
6) Stretch Goal - Run for a full work day on battery (Can Run 5 to 8 hours depending on usage)
7) Stretch Goal - Accuracy within +/- 0.5 degree Celcius (Possibly, see below)

### Notes on Accuracy
The MLX90640 thermal camera is not accurate enough for this purpose by itself. A methodology using facial detection, facial tracking, facial temperature averaging, and a multiple linear regression model was utilized. As such, the accuracy of the model is only as good as the data given to model. In our limited testing the device could indeed get +/- 0.5 celcius accuracy greater than 95% of the time. **However, Our temperature samples were limited and may not be accurate across all enviroments and populations.**

Moreover, given the limitations of this thermal camera and obtaining accurate skin temperatures via infared thermography in general, **This should only ever be used as screening device. All positive fevers should be followed up with verified method of obtaining core body temperature.**

## Core Design Overview
The basic design involves involves four components the Raspberry Pi 4 B, the MLX90640 thermal camera, a conventional (optical light) Raspberrry Pi camera, and a small 5 inch LCD screen. The thermal camera and conventional camera are placed as close as possible so thier fields of veiw overlap and they look at the same objects. The screen is used to indicate messages to the end user. The core loop of the code is as follows:

1) Conventional camera detects faces and returns their pixel coordinates
2) The 'facial' pixel coordinates are then transformed to thermal camera coordinates
3) The relevant 'facial' thermal camera pixels (which are just celcius temperatures) are used to calculate a core temperature
4) The results of the calculation are communicated to end user via a friendly UI

![image](https://user-images.githubusercontent.com/99409502/183878792-c5ec24fb-e5d1-4133-99b2-cbb46d1a874b.png)
![image](https://user-images.githubusercontent.com/99409502/183878865-9a9539d5-b326-4009-9476-f518b094951c.png)


## Hardware Components and Integration

### Necessary Components

1) Raspberry Pi 4B 2 gig variant (more memory doesn't hurt but 2 gigabytes will suffice)
2) MLX90640 55 degree FOV
3) Arducam 5MP Camera for Raspberry Pi, 1080P HD OV5647 Camera Module V1 for Pi 4 (Any Pi camera will likely work)
4) waveshare 5 inch hdmi lcd (b) 800×480 (We wouldn't suggest going less than 5 inches as the animations become very small)

### Misc. Components
These Components may not be strictly necessary depending on how one would like to build this device.
1) 3-way toggle switch for battery-off-wall operation
2) 2 Reed relays. Operating voltage ~3volts and can switch at least 500ma at 5v (used for fan and backlight, ordered off of digi-key)
3) Relay with Normally Open and Normally Closed Terminals and Trigger (Trigger not strictly necessary but was incorporated in our design)
See [Full_Schematic](https://github.com/peterWSU109/ThermalPi/blob/0f1ca807e247e0bf635c6557d95f849d3ba87a80/Senior%20Design%20Schematic%20BOTH.png) and [pi_power_button explanation](https://github.com/peterWSU109/ThermalPi/blob/59b25400a38b9f8c12cb0b1cb150e04c7f70e910/Pi_Power_Button_Explanation.jpg)

## Build Notes

### Code for misc. hardware components
The main_loop_GPIO.py file has code for an integrated hardware system. It's effected GPIO pins are explained below. The main_loop.py and main_functions.py have had any GPIO references removed.
1) GPIO 11 and GPIO 4 toggle a relay to allow for single push button on/off 
2) GPIO 23 toggles a relay that activates the screen backlight (The team directly soldered a relay to short circuit a backlight switch)
3) GPIO 24 toggles a relay that activates a case fan

### Known Issues

1) The initial ambient temperature calibration can sometimes error because a 'false' positive face is present
3) The function that adjusts for mismatched FOVs of the thermal camera and conventional camera is very basic. Could be written much better to adjust for lens distortion

## Basic Software and Component Installation
### Setting up the thermal camera
There are many guides online for setting up the MLX90640 thermal camera on the Raspberry Pi.
These guides will discuss both how to physically connect the thermal camera to Pi and the necessary software packages.

1) A very detailed written guide can be found here [adafruit-mlx90640-ir-thermal-camera](https://learn.adafruit.com/adafruit-mlx90640-ir-thermal-camera)
2) A quick and fast guide uploaded by Smart Home Everything is here https://www.youtube.com/watch?v=XRwbcsbh33w.

#### Though the guides above are great, this is a quick list of commands/steps to get the necessary packages and test the camera
1) sudo apt install python3-scipy
2) sudo apt install python3-numpy
3) sudo apt install python-smbus
4) sudo apt install python i2c-tools
5) sudo pip3 install python RPI.GPIO
6) sudo pip3 install adafruit-circuitpython-mlx90640

 *Install matplot library if following along in the video, however it is not necessary for this project*
 
 7) sudo apt install python3 matplot-lib

#### Turn on the I2C interface and set the Baud rate
1) Go to terminal and type "sudo nano config.txt"
2) On the line directly below "Uncomment some or all of these to enable the optional hardware interfaces" type the following:
      "dtparam=i2c_arm=on,i2c_arm_baudrate=400000"
3) Save changes and exit the file
4) Reboot the Raspberry Pi

#### Check if the camera is detected by the Raspberry Pi and test
*This section is different than the youtube video link*
1) Type "i2c_detect -y l" into terminal. If is detected a single integer value should be present in a grid array of underscores
2) Next run a quick test program, one is available in the reference code section in the main branch, [adacircuitpython example_code](https://github.com/peterWSU109/ThermalPi/blob/01376b959330d6dd1ddbc45c62da55b1f1fccd90/Reference_Code/Thermal_Camera_Example_Code.py)

Assuming the camera is working, you should see an intermittent refresh of ASCII characters scrolling down the screen. These characters should change as you move the camera around the room, as they represent different temperature values.

### Install the Rasberry Pi Optical Camera and Align with Thermal camera

However the cameras may be mounted, the cameras need to be aligned so thier respective fields of view (FOV) overlap as much as possible:

![camera line up](https://github.com/peterWSU109/ThermalPi/blob/d1cf1d4a702ee568faaf213b1ca062d244e2f426/images_videos/physical%20camera%20line%20up.jpg)

In the above configuration the software FOV settings should be aproximately correct.

### Final Dependencies to install

1) sudo apt-get install python-opencv
2) sudo apt-get install python-pandas
3) sudo pip install -U scikit-learn

### Execution

Put these files and folders in the same directory
1) main_loop.py
2) main_functions.py
3) haarcascades
4) assets

Then run main_loop.py

.. Or .. clone the repository (The repository was used to hold some large image files and a video, it's about ~160 megabytes)
Type the following into Terminal to execute the program:

1) git clone https://github.com/peterWSU109/ThermalPi
2) sudo ThermalPi python3 main_loop.py

Finally execute main_loop.py. The program will default into full screen mode and can be exited by pressing 'Q' on the keyboard.
Upon program starting, be sure to stay out of the way of the cameras as it is measuring the ambient temperture of the room. Have Fun!

##Ackowledgments

1)


