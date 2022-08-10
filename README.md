# Thermal Pi Project
The Thermal Pi project repository contains the code, schematics and 3D model documents to create a contactless, human body temperature screening device with a Raspberry Pi. This prototype was created as a Senior design project at Wichita State University in Spring 2022 by Peter M., Lexi W., Shaima H., and Adrian S.


![image](https://user-images.githubusercontent.com/99409502/183681615-91228a1e-6a97-4f3c-8c00-d679fa8c1665.png)
![image](https://user-images.githubusercontent.com/99409502/183681972-60288032-311e-4323-a0b5-ae1a2fa4eb10.png)
![image](https://user-images.githubusercontent.com/99409502/183682458-b8451d3c-55b2-4d2e-822c-af865bdd11c3.png)

See video for basic demonstration [Video_demonstration](https://github.com/peterWSU109/ThermalPi/blob/796d23c62aa1abba13014b9afdf617d7c37640e8/images_videos/Thermal%20Scanner%20Demo.mp4)


## Design Goals/Specifications

1) Small (Able to be held with one hand), and lightweight (Achieved!)
2) Screen people at a distance 3 to 6 feet (Achieved!)
3) Complete screening in less than 3 seconds (Achieved!)
4) Create friendly UI for the end user (Acheived!)
5) Stretch Goal - Measure multiple users at once (Acheived!)
6) Stretch Goal - Run for a full work day on battery (Can Run 5 to 8 hours depending on usage)
7) Stretch Goal - Accuracy within +/- 0.5 degree Celcius (Possibly, see below)

### Notes on Accuracy
The MLX90640 thermal camera is not accurate enough for this purpose by itself. A methodology using facial detection, facial tracking, facial temperature averaging, and a multiple linear regression model was utilized. As such, the accuracy of the model is only as good as the data given to model. In our limited testing the device could indeed get +/- 0.5 celcius accuracy greater than 95% of the time. **However, Our temperature samples were limited and may not be accurate across all enviroments and populations.**

Moreover, given the limitations of this thermal camera and obtaining accurate skin temperatures via infared thermography in general, **This should only ever be used as screening device**. All positive fevers should be followed up with verified method of obtaining core body temperature

## Core Design Overview
The basic design involves involves four components the Raspberry Pi 4 B, the MLX90640 thermal camera, a conventional (optical light) Raspberrry Pi camera, and a small 5 inch LCD screen. The thermal camera and conventional camera are placed as close as possible so thier fields of veiw overlap and they look at the same objects. The screen is used to indicate messages to the end user. The core loop of the code is as follows:

1) Conventional camera detects faces and returns their pixel coordinates
2) The 'facial' pixel coordinates are then transformed to thermal camera coordinates
3) The relevant 'facial' thermal camera pixels (which are just celcius temperatures) are used to calculate a core temperature
4) Indicate results of calculation via friendly UI

![image](https://user-images.githubusercontent.com/99409502/183878792-c5ec24fb-e5d1-4133-99b2-cbb46d1a874b.png)
![image](https://user-images.githubusercontent.com/99409502/183878865-9a9539d5-b326-4009-9476-f518b094951c.png)

**The images show the conversion from raw thermal and image data to a friendly UI**

## Hardware Components

## Current Build Notes

### Hardware Tie-ins

The current build has code for various hardware components toggled via GPIO pins, It requres two scripts to run at Pi start up:

1) GPIO 11 and GPIO 4 toggle a relay to allow for single push button on/off, see [pi_power_button explanation](https://github.com/peterWSU109/ThermalPi/blob/59b25400a38b9f8c12cb0b1cb150e04c7f70e910/Pi_Power_Button_Explanation.jpg)
2) GPIO 23 toggles a relay that activates the screen backlight (The team directly soldered a relay to short circuit a backlight switch)
3) GPIO 24 toggles a relay that activates a case fan

### Known Issues

1) Code - The initial ambient temperature calibration can sometimes error because 'false' positive face is present
2) hardware The 3D printed enclosure design can fit the hardware inside, but DOES NOT have effective mounts - We used some hot glue and drill to make it work :)

## Installation




