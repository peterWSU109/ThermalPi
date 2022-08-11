import main_functions as mf
import threading
import time
import cv2
import numpy as np
import math
import pandas as pd
import os
from sklearn.linear_model import LinearRegression

#Display most recent temp in left hand corner
display_temp = True


#Distance and raw_temp limits - ignores results at fringe measurements
limits_on = True
distance_limit = 200
raw_temp_limit = 29


#debug toggles
debug = False
#if rapid cycle is false will just show graph and camera vision
if debug == True:
    rapid_cycle = True
#Record raw uncorrected temps
raw_temp = False
#Run a quick regression on the data - otherwise just test the current model - will want to set raw temps to True
quick_regression = False
#Save the Calculated Temps/Ratios/Ambient temp/ Distance to a Dataframe File
send_to_file = False
#For Debug - ensures each calculated temperature is done from narrow range of distances
distance_control = False
#For Debug - Represents the validated control temp for regression analysis
my_temp = 36.9


#basic font settings from openCV
font = cv2.FONT_HERSHEY_SIMPLEX
color = (0,255,0)
thickness = 1
fontScale = 0.6

#haarcascade algorithmn openCV uses to detect faces in images
face_cascade = cv2.CascadeClassifier('/home/pi/Desktop/haarcascades/opencv_haarcascade_frontalface_alt.xml')
face_cascade_2 = cv2.CascadeClassifier('/home/pi/Desktop/haarcascades/haarcascade_frontalface_default.xml')


#video capture settings
cap = cv2.VideoCapture(0)
cap.set(3,mf.h_res)
cap.set(4,mf.v_res)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

#Possible Fever  RGB(255,127,39)
#Move Closer  RGB(0,0,255)
#Fever Free  RGB(0,0,255)
#Too Close RGB(255,242,0)
#Possible Forehead Obstruction D(87,52) RGB(163,73,164)
#Calculating  RGB(127,127,127)
#Face Screen RGB(63,72,204)

#How many frames for the background to cycle
background_cycle_frame = 100
file_list = os.listdir(os.getcwd() + "/assets")
file_list.sort()

#background array and string path
backgrounds = []
string_bkrg_path = ""

#Loads calibration sceen and Graph
calibraton = cv2.imread("/home/pi/Desktop/assets/calibraton.jpg")
graphic = cv2.imread("/home/pi/Desktop/assets/graph_800x480.jpg")

for background in file_list:
    if background.find("room") > -1:
        backgrounds.append("/home/pi/Desktop/assets/" + background)

string_bckgrd_path = backgrounds[0]


#calibration and debug
if debug == True:
    string = str(my_temp)
    cv2.line(graphic, (0,480 - int((my_temp-30)*50)), (800,480 - int((my_temp-30)*50)), (0,255,0), 1)
    cv2.putText(graphic, string, (25,470 - int((my_temp-30)*50)), font, 0.5, (0,0,0),1, cv2.LINE_AA, False)
    cv2.line(graphic, (0,480 - int((7.2)*50)), (800,480 - int((7.2)*50)), (255,0,255), thickness)
    cv2.line(graphic, (0,480 - int((5)*50)), (800,480 - int((5)*50)), (255,0,255), thickness)
    cv2.imshow('graph', graphic)

#Arrays that hold all information for ML model
values = []
residuals = []
def_temps = []
ambient_temp = []
standard_dev = []

#Debug regression analysis cycles
debug_temp_limit = 100000
debug_temp_count = debug_temp_limit
debug_person_count = 0
debug_color = (0,0,255)

#keeps track of faces
people = []



def draw_stick_figure(bckgrd, top_right_corner , scale, thickness):
    #head
    x , y = top_right_corner
    #modified for banners and rectangle
    x = int(x + 15)
    y = int(y + 15)
    y = y - 115 # funtion will draw stick figure from bottom right corner 
    cv2.circle(bckgrd, (x + int(20*scale), y + int(20*scale)), int(15*scale), (0,255,255), -1)
    cv2.circle(bckgrd, (x + int(20*scale), y + int(20*scale)), int(15*scale), (0,0,0), thickness)
    #eyes
    cv2.line(bckgrd, (x + int(15*scale), y + int(13*scale)), (x + int(15*scale), y + int(20*scale)), (0,0,0), thickness)
    cv2.line(bckgrd, (x + int(25*scale), y + int(13*scale)), (x + int(25*scale), y + int(20*scale)), (0,0,0), thickness)
    #mouth
    mouth = np.array([[x + int(11*scale), y + int(22*scale)], [x + int(17*scale), y + int(27*scale)], [ x + int(23*scale), y + int(27*scale)], [x +int(29*scale), y + int(22*scale)]], np.int32)
    mouth.reshape(-1,1,2)
    cv2.polylines(bckgrd, [mouth], False, (0,0,0), thickness)
    #torso
    cv2.line(bckgrd, (x + int(20*scale), y + int(35*scale)), (x + int(20*scale), y + int(95*scale)), (0,0,0), thickness)
    #arms
    cv2.line(bckgrd, (x + int(5*scale), y + int(65*scale)), (x + int(35*scale), y + int(65*scale)), (0,0,0), thickness)
    
    #legs
    cv2.line(bckgrd, (x + int(20*scale), y + int(95*scale)), (x + int(5*scale), y + int(110*scale)), (0,0,0), thickness)
    cv2.line(bckgrd, (x + int(20*scale), y + int(95*scale)), (x + int(35*scale), y + int(110*scale)), (0,0,0), thickness)

def draw_coffee_cup(bckgrd, x, y, scale, thickness):
    #draws outline of coffee mug
    cv2.ellipse(bckgrd,(x,y),(int(15*scale),int(10*scale)),0,0,360,(0,0,0),thickness)
    cv2.ellipse(bckgrd,(x,y+int(23*scale)),(int(15*scale),int(10*scale)),0,0,360,(0,0,0),thickness)
    cv2.rectangle(bckgrd,(x-int(15*scale),y+int(3*scale)),(x+int(15*scale),y+int(26*scale)),(0,0,0),thickness)
    
    #fills in the above outlines with color
    cv2.rectangle(bckgrd,(x-int(15*scale),y+int(3*scale)),(x+int(15*scale),y+int(26*scale)),(255,236,221),-1)
    cv2.ellipse(bckgrd,(x,y),(int(15*scale),int(10*scale)),0,0,360,(0,64,96),-1)
    cv2.ellipse(bckgrd,(x,y+int(23*scale)),(int(15*scale),int(10*scale)),0,0,360,(255,236,221),-1)
    
    #Draws a handle
    handle = np.array([[x + int(15*scale), y + int(3*scale)], [x + int(22*scale), y + int(9*scale)], [ x + int(22*scale), y + int(17*scale)],
                       [x +int(15*scale), y + int(24*scale)]], np.int32)
    handle.reshape(-1,1,2)
    cv2.polylines(bckgrd, [handle], False, (0,0,0), thickness)
    

# Messages
obstruction_message = "Obstruction error - Could be caused by clothing articles covering face(such as hat), or prespiration covering forehead."
too_cool_message = "Too Cool - This can happen if walking inside from a cold enviroment. If this occurs please allow face to warm indoors and try again in few minutes."
fever_message = "Though a fever has been detected, contactless thermometers can occassionally report false positives. It is recommended this fever is confirmed with a retail home method such an oral or tympanic thermometer"
#57 horizontal characters - x 5 lines at 0.8 font_size (285 characters) is about the max
def display_message(bckgrd, string, color, text_color, font_size, timer):
    strings = []
    str_len = len(string)
    str_ind = 57
    while(str_len > 0):
        if str_len > 57:
            while string[str_ind] != " ":
                str_ind = str_ind - 1
            strings.append(string[:str_ind])
        else:
            strings.append(string)
            break
        string = string[str_ind:]
        str_len = str_len - str_ind
        str_ind = 57
    cv2.rectangle(bckgrd, (8,455 - (len(strings) - 1)*45),(788,470),color,-1)
    cv2.rectangle(bckgrd, (6,455 - (len(strings) - 1)*45),(790,472),(0,0,0),2)
    for i in range(0, len(strings)):
        cv2.putText(bckgrd, strings[i], (18,470 - (len(strings) - 1)*40 + i*28), font, 0.8, text_color,2, cv2.LINE_AA, False)
    cv2.putText(bckgrd, str(1 + int(timer/10)), (750,445), font, 0.8, text_color,2, cv2.LINE_AA, False)   


#Thermal camera function and thread - works in background continously


t_camera = threading.Thread(target = mf.refresh_thermalCamera, daemon = True)
t_camera.start()

    

while True:
    
    faces = []
    #Will only search for faces if the thermal camera has recently detected movement
    #This counter is decremented with each loop, but reset everytime there is movement
    if mf.movement_detected_timer > 0:
        #changes background image 
        if mf.frame_count < len(backgrounds)*background_cycle_frame:
            if mf.frame_count%background_cycle_frame == 0:
                string_bckgrd_path = backgrounds[int(mf.frame_count/background_cycle_frame)]
        else:
            mf.frame_count = -1

        #obtains image from raspberry pi camera, flips image related to physical hardware restraints
        #creates a grayscale image for the haarcascade face finder algorithmn and then uses
        #a histogrophic equalizer to improve image contrast for facial detection
        ret, fram = cap.read()
        fram = cv2.flip(fram, 180)
        gray_p = cv2.cvtColor(fram, cv2.COLOR_BGR2GRAY)
        gray_p = cv2.equalizeHist(gray_p)
        
        #runs two facial algorithmns to find faces
        #non faces weeded out by thermal camera
        
        faces_1 = face_cascade.detectMultiScale(gray_p, 1.2, 2)
        faces_2 = face_cascade_2.detectMultiScale(gray_p, 1.2, 2)
        for (a,b,c,d) in faces_1:
            faces.append((a,b,c,d))
        for (a,b,c,d) in faces_2:
            faces.append((a,b,c,d))
        
        #finds duplicate faces that are too close together
        #It keeps all faces from the initial pass of the first algorithm
        #Then it removes any face in faces_2 that is close at all to any face in faces_1
        if len(faces) > 1:
            faces_length = len(faces)
            for i in range(0,len(faces_1)):
                (a,b,c,d) = faces[i]
                for j in range(len(faces_1),faces_length):
                    (x,y,z,w) = faces[j]
                    if x - 0.5*c < a < x + 0.5*c and y - 0.5*d < b < y + 0.5*d:
                        faces[j] = (0,0,0,0)
                    if x - 40 < a < x + 40 and y - 40 < b < y + 40:
                        faces[j] = (0,0,0,0)
      
        #removes duplicate faces
        duplicate_faces = True
        while duplicate_faces == True:
            duplicate_faces = False
            for i in range(0, len(faces)):
                if faces[i] == (0,0,0,0):
                    faces.pop(i)
                    duplicate_faces = True
                    break
            

    if len(faces) > 0:
        mf.face_is_present = True
                
    #creates a window to display thermal image over real image
    if debug == True:
        b, g, r = cv2.split(fram)
        r = mf.create_thermal_image( r )
        fram = cv2.merge([b,g,r])
        #displays sleep timer in upper left
        mf.fram = cv2.putText(fram, str(mf.movement_detected_timer), (0,30), font, 1.5, (0,125,0), 1, cv2.LINE_AA, False) 
        
    
    
    #def__init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, temp = 32.5)
    #update the faces list

    
    for (a, b, c, d) in faces:
        if debug == True:
            cv2.rectangle(fram, (a,b), (a+c, b+d), (255,0,0),2)
     
        distance = mf.distance(c, mf.global_face_area )
        number_of_max_temps = int(mf.num_max_temps(distance, mf.global_forehead))
        #print(number_of_max_temps)
        if mf.frame:
            temperatures = (mf.get_n_max_temps( (a,b), (a+c, b+d), number_of_max_temps))
            temperatures.insert(0,distance)
        else:
            temperatures = []
            mf.frame = []
        
        #stores value for maximum face temp - never below 35
        mf.max_face_temp = 35
        if len(temperatures) > 2:
            if temperatures[-1] > mf.max_face_temp:
                mf.max_face_temp = temperatures[-1]
        
        if people:
            new_face = True
            for i in range(0,len(people)):
                #Checks if face Coordinates in updated faces array are close to any other previous face
                #if coordinates are close -> updates that face/person in people array; otherwise creates new person
                if a -18 < people[i].x < a + 18 and b-18 < people[i].y < b + 18:
                    new_face = False
                    #frames is a person attribute that cycles from 1 to 30 -> increments each frame
                    people[i].frames = people[i].frames + 1
                    people[i].sizes.append(c)  
                    
                    #keeps a running average of rectangle size
                    if len(people[i].sizes) > 4:
                        people[i].sizes.pop(0)
                        
                    
                    #print(number_of_max_temps)
                    #Every person has 10 frames before they are deleted, UNLESS, they are found and udpated
                    people[i].time_to_live = 10
                    people[i].distance = distance
                    
                    #if a person is present for 10 frames and they have living ratio they will be drawn
                    if temperatures and people[i].frames > 10 and people[i].alive == False:
                        if temperatures[1] > 0:
                            if temperatures[2]/temperatures[1] > 0.3:
                                #print("area", temperatures[1], "t_pixels", temperatures[2], "ratio", temperatures[2]/temperatures[1])
                                temps = []
                                temps.append(temperatures)
                                #if debug == True:
                                    #print("Alive? : ",mf.def_temp_calc(temps, mf.temperature_average(temperatures), raw_temp))
                                    #print(temperatures)
                                if mf.def_temp_calc(temps, mf.temperature_average(temperatures), raw_temp) >= 35.0 and raw_temp == True:
                                    if limits_on == True:
                                        if temperatures[0] < distance_limit and mf.temperature_average(temperatures) > raw_temp_limit:
                                            people[i].alive = True
                                    else:
                                        people[i].alive = True
                                    if temperatures[3] > 2:
                                        people[i].def_temp = 1
                                    else:
                                        people[i].def_temp = 0
                                else:
                                    people[i].alive = True
                    
                        
                    #For the coffee Detector - remove coffee that is gone
                    if people[i].coffee_ttl > 0:
                        people[i].coffee_ttl = people[i].coffee_ttl -1
                    else:
                        people[i].has_coffee = False
                        
                       
                    #temp -2 = face screen; temp of -1 = Too close; temp 0 = move closer; temp 1 = calculating; temp 2 == possible obstruction; and temp 3 = calculated temp < 35.0
                    #temp -3 = outside of thermal camera FOV, temp -4 "Stand STILL' - when standard dev of raw temps is too high (>1)
                    if temperatures and people[i].frames%3 == 0 and people[i].def_temp < 35.0 and people[i].obstruction_count > 0:
    
    
                        #move retry incrementer - won't instantly tell person to move forward if a single temp array was bad - will show "calculating"
                        if people[i].move_retry == 0 and people[i].distance < 100: 
                            new_def_temp = 0
                        else:
                            people[i].move_retry = people[i].move_retry - 1
                            new_def_temp = 1
                        #motion between thermal camera frames - "face screen"
                        if not (a - mf.tc_horz_scale < people[i].last_therm_x < a + mf.tc_horz_scale and b - mf.tc_vert_scale < people[i].last_therm_y < b  + mf.tc_vert_scale):
                            new_def_temp = -2
                        people[i].last_therm_x = a
                        people[i].last_therm_y = b
                        #temp -3 = move towards face towards center of screen, face is outside thermal FOV but in camera FOV
                        if temperatures[1] == -1:
                            people[i].def_temp = -3
                        #needs at least 1 pixel to be considered for calculation and person is in FOV of thermal camera
                        if temperatures[2] >= 1 and new_def_temp > -2:
                            #possible obstruction -> less than 50% of face > relevent temp and person is close to camera 
                            if temperatures[2]/temperatures[1] <= 0.5 and people[i].distance < 100 and people[i].obstruction_count > 0:
                                people[i].obstruction_count = people[i].obstruction_count - 1
                                new_def_temp = 2
                            #calculated temp < 35.0 per calculated def_temp function
                            elif people[i].def_temp == 3 and people[i].obstruction_count > 0:
                                people[i].obstruction_count = people[i].obstruction_count - 1
                            #calculating - appends new temp array 
                            elif temperatures[2]/temperatures[1] > 0.50 and temperatures[1] <= 500 and len(temperatures) > 4:
                                #provides distance control
                                if distance_control == True and len(people[i].temps) > 0:
                                    if temperatures[0] - 15 < people[i].temps[0][0] < temperatures[0] + 15:
                                        people[i].temps.append(temperatures)
                                        people[i].total_temps = people[i].total_temps + len(temperatures) - 4
                                        new_def_temp = 1
                                        people[i].move_retry = 3
                                    else:
                                        people[i].temps = []
                                        people[i].total_temps = 0
                                        new_def_temp = -4
                                else:
                                    people[i].temps.append(temperatures)
                                    people[i].total_temps = people[i].total_temps + len(temperatures) - 4
                                    new_def_temp = 1
                                    people[i].move_retry = 3
                                
                            #too close - if person's face takes up over 500/768 thermal pixels
                        if temperatures[1] > 500:
                            new_def_temp = -1
                        #definitive temperature
                        if people[i].total_temps >= 16:
                            people[i].standard_dev = people[i].temp_array_std()
                            people[i].average_temp = people[i].temp_array_average()
                            if people[i].standard_dev > 0.7:
                                people[i].temps = []
                                people[i].total_temps = 0
                                new_def_temp = -4
                            else:
                                new_def_temp = mf.def_temp_calc(people[i].temps, people[i].average_temp, raw_temp)
                                if debug == True:
                                    people[i].w_distance = mf.weighted_average(people[i].temps, 0)
                                    people[i].w_area = mf.weighted_average(people[i].temps,1 )
                                    people[i].w_t_pixels = mf.weighted_average(people[i].temps,2 )
                        people[i].def_temp = new_def_temp
                        
                        #reset frame
                        if people[i].frames == 30:
                            people[i].frames = 0
                    #This reduces jitter, Last_x and Last_y will be used to draw the stick figure but are only
                    #udpated if x, y, of person has changed significantly
                    if not (a -3 < people[i].x < a + 3 and b-3 < people[i].y < b + 3):
                        people[i].last_x = a
                        people[i].last_y = b
                    people[i].x = a
                    people[i].y = b
                    if not people[i].size -2 < np.average(people[i].sizes) < people[i].size + 2:
                            people[i].size = int(np.average(people[i].sizes))
                    

            if new_face == True:
                people.append(mf.person(a,b,a,b,15,1,1,c,a,b))
                
        else:
            people.append(mf.person(a,b,a,b,15,1,1,c,a,b))
            
    #update mf.person_is_present
    mf.person_is_present = False
    for i in range(0, len(people)):
        if people[i].alive == True:
            mf.person_is_present = True
    
    
    
    #coffee detector code
    #Finds objects that are not in a face, and are at least 2C hotter than
    #any other than the hottest face
    
    coffee = []
    if mf.person_is_present == True:
        for i in range(0,768):
            if mf.max_face_temp + 2 < mf.frame[i] < 45:
                coffee.append(mf.thermal_to_image((i%32,(i-i%32)/32)))
    real_coffee = []
    if coffee:
        real_coffee.append(coffee[0])
        a,b = coffee[0]
        a = int(a)
        b = int(b)
        if debug == True:
            cv2.rectangle(fram, (a,b), (a+25,b+25), (0,255,0),2)
        for (x,y) in coffee:
            new_coffee = True
            for (a,b) in real_coffee:
                #checks for duplicate coffees
                if a-30 < x < a+30 and b - 20 < y < b + 80:
                    new_coffee = False
            if new_coffee == True:
                real_coffee.append((x,y))
                x = int(x)
                y = int(y)
                if debug == True:
                    cv2.rectangle(fram, (x,y), (x+25,y+25), (0,255,0),2)
    
    #Once coffees are found - finds person with closest right hand corner to coffee,
    # and then switches there "has Coffee" attribute equal to True
    if real_coffee:
        distance = 1000
        person_num = 0
        for (x,y) in real_coffee:
            for j in range(0, len(people)):
                if people[j].y + people[j].size < y:
                    magnitude = (y - people[j].y + people[j].size)**2 + (people[j].x - x)**2
                    magnitude = magnitude**0.5
                    if distance > magnitude:
                        person_num = j
                    distance = magnitude
            people[person_num].has_coffee = True
            people[person_num].coffee_ttl = 10
                
                
       
        
        

    #udpate people list/ deletes person when ttl is 0
    dead_faces = True
    while(dead_faces == True):
        dead_faces = False
        for i in range(0,len(people)):
            if people[i].time_to_live <= 0:
                people.pop(i)
                dead_faces = True
                break
           
    #obstruction message D(800,212)
    #fever message D(799,100)
    #This loop iterates through the people array and draws them on the background
    #If they are alive and an initial ambient temp has been measured
    if people:
        mf.face_is_present = True
        for i in range(0,len(people)):
            people[i].time_to_live = people[i].time_to_live - 1
            if people[i].alive == True and mf.ambient > 0:
                a = people[i].last_x
                b = people[i].last_y
                bckgrd_coord = mf.fram_to_background((a,b))
                x, y = bckgrd_coord
                bckgrd_coord = x, y
                font = cv2.FONT_HERSHEY_SIMPLEX
                thickness = 2
                fontScale = 0.8
                bgr = (0,0,0)
                #This sets the banner message above the stick figures head
                if people[i].def_temp == -4:
                    #Standard Deviation of Temps to High
                    color = (255,255,255)
                    bgr = (255,0,0)
                    fontScale = 0.7
                    string = "Too much movement"
                elif people[i].def_temp == -3:
                    #Person is outside the thermal FOV but in Camera FOV
                    color = (0,0,0)
                    bgr = (0,242,255)
                    fontScale = 0.7
                    string = "Move to Center"
                elif people[i].def_temp == -2:
                    #Motion between frames greater than one thermal pixel length
                    color = (255,255,255)
                    bgr = (255,0,0)
                    string = "Face Screen"
                elif people[i].def_temp == -1:
                    color = (0,0,0)
                    bgr = (0,242,255)
                    string = "Too Close"
                elif people[i].def_temp == 0:
                    color = (255,255,255)
                    bgr = (255,0,0)
                    string = "Move Closer"
                elif people[i].def_temp == 1:
                    color = (255,255,255)
                    bgr = (127,127,127)
                    string = "Calculating"
                elif people[i].def_temp == 2:
                    color = (255,255,255)
                    bgr = (164,73,163)
                    fontScale = 0.7
                    string = "Possible obstruction"
                    if people[i].obstruction_count == 0:
                        mf.obstruction_message_timer = 80
                elif people[i].def_temp == 3:
                    #calculated temp is less than 35.0
                    color = (0,0,0)
                    bgr = (234,217,153)
                    fontScale = 0.7
                    string = "Face is too Cool"
                    if people[i].obstruction_count == 0:
                        mf.cool_message_timer = 80
                elif mf.rel_temp < people[i].def_temp < 37.3:
                    color = (0,0,0)
                    bgr = (0,255,0)
                    string = "Fever Free"
                    cv2.rectangle(bkrg, (0,0), (380,60), (0,255,0),-1)
                    bkrg = cv2.putText(bkrg, "Fever Free!", (0,50), font, 2, (0,0,0), 2, cv2.LINE_AA, False)
                elif 37.3 <= people[i].def_temp:
                    color = (0,0,0)
                    bgr = (39,127,255)
                    fontScale = 0.7
                    string = "Possible Fever"
                    mf.fever_message_timer = 80
                
                #displays temp if equal to true
                if display_temp == True:
                    cv2.rectangle(bkrg, (600,0), (800,60), (0,255,0),-1)
                    my_temp_string = str(int(people[i].def_temp*10)/10)
                    bkrg = cv2.putText(bkrg, my_temp_string, (600,50), font, 2, (0,0,0), 2, cv2.LINE_AA, False)
                               
                
                #Sets scale and length for text above stick figure's head
                scale_factor = .5 + (people[i].size-40)/75
                length = len(string)*14 
                
                #Draws the box around stick figure and text and scales them appropriately based on distance
                #string2 = str(people[i].def_temp)
                cv2.rectangle(bkrg, (x,y-110), (x+80+int(35*(scale_factor)), y-40+int(35*(scale_factor))), bgr,2)
                cv2.rectangle(bkrg, (x,y-130), (x+length, y-107), bgr,-1)
                bkrg = cv2.putText(bkrg, string, (x,y-110), font, fontScale, color, thickness, cv2.LINE_AA, False)
                #bkrg = cv2.putText(bkrg, string2, (0,30), font, 1.5, (0,0,0), 1, cv2.LINE_AA, False)
                
                #Draws the animations for stick and coffee
                if people[i].has_coffee == True:
                    draw_coffee_cup(bkrg, x+5, y-40+int(35*scale_factor) , 0.5 + scale_factor, 2)
                if 40 <= people[i].size:
                    draw_stick_figure(bkrg, (x,y),(1+scale_factor), 2)
                elif people[i].size < 40:
                    draw_stick_figure(bkrg, (x,y),1.5 , 2)
                    

                if debug == True:
                    #draws box and temps onto thermal overlay window = 'fram'
                    string = "Temp" + str(int(people[i].def_temp*10)/10)
                    mf.fram = cv2.putText(fram, string, (a, b), font, fontScale, (0,242,255), thickness, cv2.LINE_AA, False)
                    
                    
                    if people[i].def_temp > 25 and debug_temp_count > 0:
                        x_cor = 25 + int(people[i].w_distance*3)
                        y_cor = 480 - int(((people[i].def_temp-30)*50))
                        cv2.circle(graphic, (x_cor,y_cor), 3, debug_color, -1)
                        cv2.imshow('graph', graphic)
                        
                        #Collects the residuals between the measured temp and the manually enterd real temp
                        #along with people values for regression later on
                        def_temps.append(people[i].def_temp)
                        values.append((people[i].w_distance, people[i].w_t_pixels/people[i].w_area))
                        residuals.append(my_temp - people[i].def_temp)
                        ambient_temp.append(mf.ambient)
                        standard_dev.append(people[i].standard_dev)
                        
                        #this resets a person temp information so they will be constantly remeasured
                        if rapid_cycle == True:
                            print("temp ",round(people[i].def_temp,1), "distance ", people[i].w_distance, "area ", people[i].w_area, end = "")
                            print(" t_pixels ", people[i].w_t_pixels, "ratio ",people[i].w_t_pixels/people[i].w_area, "standard_dev ", people[i].standard_dev)
                            people[i].def_temp = 0
                            people[i].temps = []
                            people[i].total_temps = 0
                            
        
                        #if debug is true the following code will collect tempatures in sets and occassionally ask for new temperatures
                        #if a new participate would like to be included in the data set
                        #The loop can can be ended by pressing Q
                        debug_temp_count = debug_temp_count - 1
                    elif people[i].def_temp > 25 and debug_temp_count < 1:
                        mf.debug_prompt = True
                        user_input = input("Please enter celcius temperature\n")
                        mf.debug_prompt = False
                        my_temp = float(user_input)
                        string = str(user_input)
                        print(people[i].def_temp)
                        
                        #This block rotates the color of the graph point as different partipant temperatures are tested
                        #and draws a line on the graph were the entered temperature sits
                        debug_person_count = debug_person_count + 1
                        debug_temp_count = debug_temp_limit
                        if debug_person_count%4 == 1:
                            debug_color = (200,0,200)
                        if debug_person_count%4 == 2:
                            debug_color = (127,127,0)
                        if debug_person_count%4 == 3:
                            debug_color = (127,127,127)
                        if debug_person_count%4 == 0:
                            debug_color = (0,127,0)
                        cv2.putText(graphic, string, (25,470 - int((my_temp-30)*50)), font, 0.5, debug_color, 1, cv2.LINE_AA, False)
                        cv2.line(graphic, (0,480 - int((my_temp-30)*50)), (800,480 - int((my_temp-30)*50)), (0,255,0), 1)                                                       
    else:
        mf.face_is_present = False


    #Display Messages on my background display
    if mf.fever_message_timer > 0:
        mf.fever_message_timer = mf.fever_message_timer - 1
        display_message(bkrg, fever_message, (14,201,255), (0,0,0), 0.8, mf.fever_message_timer)
        #This Banner stays on and covers any fever free message
        cv2.rectangle(bkrg, (0,0), (460,60), (14,201,255),-1)
        bkrg = cv2.putText(bkrg, "Possible Fever", (0,50), font, 2, (0,0,0), 2, cv2.LINE_AA, False)
            
    elif mf.obstruction_message_timer > 0:
        mf.obstruction_message_timer = mf.obstruction_message_timer - 1
        display_message(bkrg, obstruction_message, (164,73,163), (255,255,255), 0.8, mf.obstruction_message_timer)
    
    elif mf.cool_message_timer > 0:
        mf.cool_message_timer = mf.cool_message_timer - 1
        display_message(bkrg, too_cool_message, (234,217,153), (0,0,0), 0.8, mf.cool_message_timer)

    #if ambient is zero, the calibation background will be displayed
    if mf.ambient == 0:
        bkrg = calibraton
        if mf.face_is_present == True:
            bkrg = cv2.putText(bkrg, "Possible Face Detected", (0,50), font, 2, (0,0,0), 3, cv2.LINE_AA, False)
            
    
    #if debug is on the data graph, the normal background display and thermal over real camera will display in
    # all in separate windows 
    if debug == True:
        cv2.imshow('bckgrd', bkrg)
        bkrg = cv2.imread("/home/pi/Desktop/assets/800x480 owl on limb.jpg")  
        cv2.imshow('fram', fram)
    #In normal mode the main background display will appear in full screen mode
    else:
        cv2.namedWindow("bckgrd",cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("bckgrd", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('bckgrd', bkrg)
    bkrg = cv2.imread(string_bckgrd_path)

    
     
    #increment the global frame count
    mf.frame_count = mf.frame_count + 1
    #decrements movement detected timer if greater than 0
    if mf.movement_detected_timer > 0 and mf.person_is_present == False:
        mf.movement_detected_timer = mf.movement_detected_timer - 1
    #Will terminate main loop when the letter q is pressed
    if cv2.waitKey(1) == ord('q'):
        break


if debug == True:
    total_test_temps = len(def_temps)
    wrong_temps = 0
    #The residual array is the difference between the manually measured temperature entered by the
    # .. the programmer and the temp measured by the thermal camera
    # The independent values are the raw temperatures and the ratio of warm thermal pixels within the face rectangle
    df = pd.DataFrame(values, columns = ['distance', 'ratio'])
    df['def_temps'] = def_temps
    df['std_dev'] = standard_dev
    df['ambient'] = ambient_temp
    df['residuals'] = residuals
    
    #Will send data to file if desired
    if send_to_file == True:
        mf.debug_prompt = True
        filename = input("Please enter file name")
        mf.debug_prompt = False
        file_ext = "_d__no.pkl"
        if distance_control == True:
            file_ext = "_d_yes.pkl"
        df.to_pickle("data3/" + filename + file_ext)
    
    #This if statement will run regression analysis on the collected data from one session
    #Otherwise will simply run a quick test on the collected temperatures
    if quick_regression == True:
            
        df0 = df[['distance','ambient']].copy()
        df0['distance_temp'] = df['distance'] * df['def_temps']
        df0['ratio'] = df['ratio']
        df0['one_distance'] = 1/df['distance']
        df1 = pd.DataFrame(df["residuals"])
        #Runs regression 
        reg = LinearRegression().fit(df0,df1)
        #Prints results
        print("r^2 = ", reg.score(df0,df1))
        print("coeffecients", reg.coef_)
        print("y-intercept", reg.intercept_)
        distance_y = reg.coef_[0][0]
        ambient_y = reg.coef_[0][1]
        distance_temp_y =  reg.coef_[0][2]
        ratio_y = reg.coef_[0][3]
        one_distance_y = reg.coef_[0][4]
        y_intercept = reg.intercept_[0]
        
    
        #rounds results for drawing onto a graph
        distance_y = round(distance_y,4)
        distance_temp_y = round(distance_temp_y,4)
        ambient_y = round(ambient_y,4)
        ratio_y = round(ratio_y,4)
        one_distance_y = round(one_distance_y,4)
        y_intercept = round(y_intercept,4)
    
        #Draws String onto graph image with new distance correction equation, raw_temps, corrected temps, and number of samples
        string = "new_betas = rawT + D*" + str(distance_y) + " + 1/D*" + str(one_distance_y) + " + rawT*D*" + str(distance_temp_y) + " + ratio*"+ str(ratio_y) +" + ambient*" + str(ambient_y) + " + " + str(y_intercept)
        cv2.putText(graphic, string, (31,90), font, 0.35, (0,0,0), 1, cv2.LINE_AA, False)
        
        #Calculates how many temps fell OOR and prints the individual results to the console
        for i in range(0,len(values)):
            y = 480 - int((def_temps[i] + distance_y*values[i][0] + one_distance_y*(1/values[i][0]) + distance_temp_y*(def_temps[i]*values[i][0]) + ratio_y*values[i][1] + ambient_y*ambient_temp[i] + y_intercept - 30)*50)
            if not (-0.5 < my_temp - (((y-480)/(-50))+30) < 0.5):
                #print("480 - ", def_temps[i], " + ", temp_y, "*",values[i][0], " + ", ratio_y, "*", values[i][1])
                print("calc: ", ((y-480)/(-50))+30, " actual: ", my_temp)
                wrong_temps = wrong_temps + 1
            x = 25 + int(values[i][0]*3)
            cv2.circle(graphic, (x,y), 3, (255,0,0), -1)
    
    else:
        distance_y = mf.distance_beta 
        ambient_y = mf.ambient_beta 
        distance_temp_y = mf.distance_temp_beta 
        ratio_y = mf.ratio_beta 
        y_intercept = mf.y_intercept
        
        #Gives quick OOR data after debug mode raps up - only if collecting corrected temps
        if raw_temp == False:
            for i in range(0,len(def_temps)):
                if not (-0.5 < my_temp - def_temps[i] < 0.5):
                    print("calc: ", def_temps[i], " actual: ", my_temp)
                    wrong_temps = wrong_temps + 1
    
    
    
    #Writes all Test data as text on the graph
    string2 = "number of samples: " + str(len(values))
    string3 = "def_temp = rawT + D*" + str(round(mf.distance_beta,4)) + " + 1/D*"+ str(round(mf.one_distance_beta,4)) +" + rawT*D*" + str(round(mf.distance_temp_beta,4))  + " + ratio*"+ str(round(mf.ratio_beta,4)) + " + " + " ambient*" + str(round(mf.ambient_beta,4)) + " + " + str(round(mf.y_intercept,4))
    string4 = "Out of Range: " + str(wrong_temps)
    string6 = "Percentage OOR: " + str(wrong_temps/total_test_temps)
    string5 = "ambient temp" + str(round(mf.ambient,2))
    cv2.putText(graphic, string2, (31,255), font, 0.35, (0,0,0), 1, cv2.LINE_AA, False)
    cv2.putText(graphic, string3, (31,50), font, 0.35, (0,0,0), 1, cv2.LINE_AA, False)
    cv2.putText(graphic, string4, (31,270), font, 0.35, (0,0,0), 1, cv2.LINE_AA, False)
    cv2.putText(graphic, string6, (31,295), font, 0.35, (0,0,0), 1, cv2.LINE_AA, False)
    cv2.putText(graphic, string5, (600,25), font, 0.35, (0,0,0), 1, cv2.LINE_AA, False)
    #Saves the graph to desktop
    cv2.imwrite('/home/pi/Desktop/graphs/regression_graph.jpg', graphic)
    cv2.imshow('graph', graphic)
    
    #Prints the OOR statistics to the console
    print("Temp statistics: number out of +/-0.5 celcius and percentage Out")
    print("total temps: ", total_test_temps, "  Total temps OOR: ", wrong_temps,  "  Percentage Out: ", wrong_temps/total_test_temps)
    
    #Stops Thermal Camera Thread and allows programmer to look at graph
    mf.debug_prompt = True
    print("Press Anything to exit")
    cv2.waitKey(0)
             

cap.release()
cv2.destroyAllWindows()
exit(0)
