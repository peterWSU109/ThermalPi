# Thermal Pi Project
The Thermal Pi project repository contains the code, schematics and 3D model documents to create a human body temperature screening device with a Raspberry Pi.
This prototype was created as a Senior design project at Wichita State University in Spring 2022 by Peter M., Lexi W., Shaima H., and Adrian S.

picture [picture](images_videos/Thermal Pixels and Ratio.png)

## Dependencies

1) https://github.com/adafruit/Adafruit_MLX90640.git
2) https://github.com/opencv/opencv-python.git
3) https://github.com/scikit-learn/scikit-learn.git
4) https://github.com/pandas-dev/pandas.git

## Design Goals

1) Small (Able to be held with one hand), and lightweight (Achieved!)
2) Screen people at a distance 3 to 6 feet (Achieved!)
3) Complete screening in less than 3 seconds (Achieved!)
4) Stretch Goal - Measure multiple users at once (Acheived!)
5) Stretch Goal - Run for a full work day on battery (Can Run 5 to 8 hours depending on usage)
6) Stretch Goal - Accuracy within +/- 0.5 degree Celcius (Possibly, see below)

### Notes on Accuracy
The MLX90640 thermal camera is not accurate enough for this purpose by itself. A methodology using facial detection, facial tracking, facial temperature averaging, and a multiple linear regression model was utilized. As such, the accuracy of the model is only as good as the data given to model. In our limited testing the device could indeed get +/- 0.5 celcius accuracy greater than 95% of the time. **However, Our temperature samples were limited and may not be accurate across all enviroments and populations.**

Moreover, given the limitations of this thermal camera and obtaining accurate skin temperatures via infared thermography in general, **This should only ever be used as screening device**. All positive fevers should be followed up with verified method of obtaining core body temperature

## Core Design Overview
The basic design involves involves four components the Raspberry Pi 4 B, the MLX90640 thermal camera, a conventional (optical light) Raspberrry Pi camera, and a small 5 inch LCD screen. The thermal camera and conventional camera are placed as close as possible so there fields of veiw overlap and they look a the same objects. The screen is used to indicate messages to the end user. The core loop of the code is as follows:

1) Conventional camera detects faces and returns their pixel coordinates
2) The 'facial' pixel coordinates are then transformed to thermal camera coordinates
3) The relevant 'facial' thermal camera pixels (which are just celcius temperatures) are used to calculate a core temperature
4) if the calculated temperature is greater than 37.2 C (99.0 F) then display a message indicating 'fever', otherwise indicate 'fever free'




