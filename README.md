# Thermal Pi Project
The Thermal Pi project repository contains the code, schematics and 3D model documents to create a human body temperature screening device with a Raspberry Pi.
This prototype was created as a Senior design project at Wichita State University in Spring 2022 by Peter M., Lexi W., Shaima H., and Adrian S.

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
6) Stretch Goal - Accuracy within +/- 0.5 degree Celcius (See below)
    -The MLX90640 thermal camera is not accurate enough for this purpose by itself
    -A methodogy using facial detection, facial tracking, facial temperature averaging, and a multiple linear regression model were utilized
    -As such, the accuracy of the model is only as good as the data given to model
    -Our temperature samples were limited and may not be accurate across all enviroments and populations
