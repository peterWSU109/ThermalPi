#Contains the person object and all necessary functions except the Draw functions
import math
import board
import busio
import adafruit_mlx90640
import numpy as np
import threading
import time


#mlx90640 i2c and camera object definitions/instantiations from library
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ




#Stops the thermal camera thread, while user enters data in main loop
debug_prompt = False

#Counter for number of frames for background graphic loop
frame_count = 0

#Fever message timer
fever_message_timer = 0
obstruction_message_timer = 0
cool_message_timer = 0



#The default setting is 30 celcius but will be readjusted to 3 standard deviations above the ambient temperature
#this is used to determine the line between a face and not a face
rel_temp = 30


#ambient temperatrue of surfaces measured by thermal camera
ambient = 0

#This flag is set by the main thread to let the thermal camera thread know when a face is present
#This ensures the camera will only measure an ambient temperature when a face is not present
#and the main loop will only shut off if the movement_detected_timer is zero and a person is not present
face_is_present = False
person_is_present = False

#The thermal camera thread updates the movement_detected_timer everytime movement is detected
#As so long as the value is above 0, the main thread will continue to chug along
sleep_timer = 200
movement_detected_timer = sleep_timer


#max_face_temp stores the maximum facial temperature pixel value at any given time - this is used in the coffee detector
max_face_temp = 35
mutex_thermal = threading.Lock()

#Definitive Calculation Betas for adjusting for distance calculation
distance_beta = 0.101319756
ambient_beta = -0.21381868
distance_temp_beta = -0.00309885475
ratio_beta = -0.810204780
one_distance_beta = -60.0680791
y_intercept = 10.71865082


#Touch Screen display is 800x480
#resolution of image for use by openCV
h_res = 320 #320,640,1024
v_res = 240 #240,480,768


#Distance Calculation contants
#face areas taken from wikipedia
#99th percentile men face Breadth 16.5 * Menton to Top of Head 22.5 = 371 cm^2
#50th percentile women face Breadth 14.4 *Menton to Top of Head 17.7 = 254.88 cm^
#1st percenttile women forehead sellion to top of head 3.5 * Biocular Breadth 10.8 = 37.8 cm^2
total_pixels = h_res*v_res
global_face_area = 254.88
global_forehead = 37.8*3

#camera factors: conventional camera FOV = 54x41; thermal camera FOV 55x35
#pi*[tan(angle1/2)*d]*[tan(angle2/2)*d] = FOV area at some distance
#or: pi*tan(angle1/2)*tan(angle2/2) * d^2 --> d^2 is the unknown ,the rest is just a constant factor 
cam_factor = math.pi*math.tan(math.radians(27))*math.tan(math.radians(20.5))
therm_factor = math.pi*math.tan(math.radians(27.5))*math.tan(math.radians(17.5))


#Example: 0.30 will shrink the thermal projection onto the camera image by 30%
x_offset_factor = 0.30 
y_offset_factor = 0.30
tc_horz_scale = int((h_res//32)*(1-x_offset_factor))
tc_vert_scale = int((v_res//24)*(1-y_offset_factor))

#moves the entire thermal projection on camera image up or down, by an integer number of thermal pixels
#moving axis without shrinking may cause a segmentation fault
y_axis = tc_vert_scale*-1
x_axis = tc_horz_scale*-2


x_offset = int(h_res*(x_offset_factor/2)) - x_axis
y_offset = int(v_res*(y_offset_factor/2)) - y_axis

#d_scale or distance scale gives a factor for how area changes with increased pixel resolution, 320x240 is default (=1)
d_scale = h_res*v_res//(320*240)




#person object contains all necessary data to keep track of a face and corresponding temperature while
#face is in FOV of at least the conventional camera
class person:
    def __init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, t = 0, c = 0, last_therm_x = 0, last_therm_y = 0):
        
        self.x = x_cor
        self.y = y_cor
        self.last_x = lastx
        self.last_y = lasty
        self.last_therm_x = last_therm_x
        self.last_therm_y = last_therm_y
        self.time_to_live = ttl
        self.frames = frams
        self.def_temp = t
        self.size = c
        self.move_retry = 3
        
        self.temps = []
        self.alive = False
        self.total_temps = 0
        self.sizes = []
        self.has_coffee = False
        self.coffee_ttl = 0
        self.obstruction_count = 5
        self.distance = 0
        self.forehead = global_forehead
        self.face_area = global_face_area
        self.w_distance = 0
        self.w_t_pixels = 0
        self.w_area = 0
        self.standard_dev = 0
        self.average_temp = 0
        
    def new_face_area (self):
        for i in range(0,len(self.temps)):
            self.temps[i][0] = distance(self.size,self.face_area)
            self.temps[i][3] = int(num_max_temps(self.temps[i][0], self.forehead))
            if self.temps[i][3] < 1:
                self.temps[i][3] = 1
    
    def temp_array_number_max(self):
        counter = 0
        #temps = [[distance][area_of_facial_detection][number_of_likely_face_pixels][max_temps][hot_temp1]...[..hottest_temp n]
        for i in range(0, len(self.temps)):
            counter = counter + self.temps[i][3]
        return counter
    
    def temp_array_number(self):
        self.total_temps = 0
        #temps = [[distance][area_of_facial_detection][number_of_likely_face_pixels][max_temps][hot_temp1]...[..hottest_temp n]
        for i in range(0, len(self.temps)):
            for j in range(4,len(self.temps[i])):
                self.total_temps = self.total_temps + 1
        
    def temp_array_std(self):
        std_dev = 0
        temp = []
        length = 0
        #temps = [[distance][area_of_facial_detection][number_of_likely_face_pixels][max_temps][hot_temp1]...[..hottest_temp n]
        for i in range(0, len(self.temps)):
            if self.temps[i][3] + 4 <= len(self.temps[i]):
                length = self.temps[i][3] + 4
            else:
                length = len(self.temps[i])
            for j in range(4,length):
                temp.append(self.temps[i][j])
        std_dev = np.std(temp)
        return std_dev
        
    def temp_array_average(self):
        average = 0
        temp = []
        length = 0
        #temps = [[distance][area_of_facial_detection][number_of_likely_face_pixels][max_temps][hot_temp1]...[..hottest_temp n]
        for i in range(0, len(self.temps)):
            if self.temps[i][3] + 4 <= len(self.temps[i]):
                length = self.temps[i][3] + 4
            else:
                length = len(self.temps[i])
            for j in range(4,length):
                temp.append(self.temps[i][j])
        average = np.average(temp)
        return average
        
        
       

#initializes thermal frame to all zeros
frame = [0] * 768
    
#This function runs as a seperate thread in the main loop to update thermal pixel values
def refresh_thermalCamera():
    global fan_timer_limit
    global thermal_limit
    global raw_temp_cutoff
    global ambient
    global face_is_present
    global rel_temp
    global movement_detected_timer

    fan_timer = 0
    #This frame holds the temp values for movement analysis
    movement_frame = []
    #gets 32x24 frame of thermal pixels from thermal camera camera
    while True:
        if debug_prompt == False:
            try:
                mutex_thermal.acquire()
                mlx.getFrame(frame)
                mutex_thermal.release()
            except ValueError:
                continue
        #This array holds the middle 95% of temperatures
        adj_frame = []
        
        #This if statement updates the temperature after the intial setup
        if frame and face_is_present == False and ambient > 0 and debug_prompt == False:
            mean = np.average(frame)
            std_dev = np.std(frame)
            for i in range(768):
                if mean - 2*std_dev < frame[i] < 2*std_dev + mean:
                    adj_frame.append(frame[i])
            mean = np.average(adj_frame)
            std_dev = np.std(adj_frame)
            if (ambient - 2 < mean < ambient + 2) and std_dev < 2*((rel_temp-mean)/3) or ambient == 0:
                ambient = mean
                rel_temp = 3*std_dev + ambient
                #print(rel_temp, ambient)
                
        #This statement calculates the inital startup ambient temp
        elif frame and face_is_present == False and ambient == 0 and frame_count > 30 and debug_prompt == False:
            mean = np.average(frame)
            std_dev = np.std(frame)
            for i in range(768):
                if mean - 2*std_dev < frame[i] < 2*std_dev + mean:
                    adj_frame.append(frame[i])
            ambient = np.average(adj_frame)
            rel_temp = 3*(np.std(adj_frame)) + ambient + 2
            raw_temp_cutoff = rel_temp + 2
            print(rel_temp, ambient)
            
        #Detects movement by looking for changes in thermal pixel values between frames
        if movement_frame and frame and debug_prompt == False:
            for i in range(0,96):
                if not (-3 < frame[i*8] - movement_frame[i] < 3):
                    movement_detected_timer =  sleep_timer
        for i in range(0,96):
            movement_frame.append(frame[i*8])
        
                
        

                

#Notes on how the picture to background draw works
#floor of background
# lower x range from 0 to 800 but 0 to 500 at y = 210
# y range = 210 to 480
#y_transform = ((top_right_y/v_res)*270) + 210
#stick figure is 115 pixels tall at one scale
#x coordinate transform  x_adjust = (top_right_x/h_res)*(500 + (y_transform-210/270)*300) for strgith to 800x480
#above will get us 'squeezed' but still need x_offset
#x_transform = x_adjust - 150*(y_transform - 480/270)
#y_transform - 115

def fram_to_background( top_right_corner ):
    top_right_x, top_right_y = top_right_corner
    y_transform = ((top_right_y/v_res)*270) + 210
    pos_y_slope = ((y_transform - 210)/270) # y 0 to positive 1 as y increases
    neg_y_slope = ((y_transform - 480)/270) # y -1 to 0 as y increases
    
    x_transform = (top_right_x/h_res)*500 + (pos_y_slope*300) - 150 * (neg_y_slope)
    
    x_transform = int(x_transform)
    y_transform = int(y_transform)
    return ([x_transform, y_transform])
    
 


def cel_to_far( t ):
    t = ((t*9)/5)+32
    return t

   

#calculates the Definitive temperature of a person
def def_temp_calc( temps, std_dev, ave_temp, raw_temp):
    correction = 0
    def_temp = 0
    temp = []
    temp_length = 0
    #temps = [[distance][area_of_facial_detection][number_of_likely_face_pixels][std_dev of rel. temps][hot_temp1]...[..hottest_temp n]
    if len(temps) > 0:
        for i in range(0, len(temps)):
            correction = 0
            if temps[i][3] + 4 <= len(temps[i]):
                temp_length = temps[i][3] + 4
            else:
                temp_length = len(temps[i])
            #print('distance', round(temps[i][0]), "area",temps[i][1],"t_pixels", temps[i][2] ,"ratio", temps[i][2]/temps[i][1])
            if raw_temp == False:
                correction = distance_beta*temps[i][0]  +  ratio_beta*temps[i][2]/temps[i][1] +ambient*ambient_beta + one_distance_beta*(1/temps[i][0]) +distance_temp_beta*(ave_temp*temps[i][0]) + y_intercept
                #print("correction: ", correction)
            for j in range(4,temp_length):
                temp.append(temps[i][j] + correction)
            #print(" distance", temps[i][0], "correction ", correction, " def_temp", temp + correction)
    else:
        return 0

    def_temp = np.average(temp)
    if def_temp < 35.0 and raw_temp == False:
        print(def_temp)
        if temps[-1][0] < 100:
            def_temp = 3
        else:
            #person is cool, but far away - tells them to move closer
            def_temp = 0
    #print("ave_temp", def_temp, "distance", temps[-1][0],"\n")
    return def_temp



    

def temperature_std (temps):
    temp = []
    if len(temps) > 4:
        for i in range(4, len(temps)):
            temp.append(temps[i])
    return np.std(temp)

def temperature_average (temps):
    temp = []
    if len(temps) > 4:
        for i in range(4, len(temps)):
            temp.append(temps[i])
    return np.average(temp)



#distance calculator
def distance( c , face_area):
    #the face area is cm^2, so will return distance in cm
    ratio = c**2/total_pixels
    distance = (face_area/ratio)/cam_factor
    distance = math.sqrt(distance)
    
    return distance


    
def num_max_temps( d, forehead ):
    num_temps = therm_factor*(d**2)
    num_temps = (forehead/num_temps)*768
    
    return num_temps  


#takes a thermal tuple and returns the corresponding image tuple
def thermal_to_image( t_pixel ):
    x, y = t_pixel
    x = (x*tc_horz_scale) + x_offset
    y = (y*tc_vert_scale) + y_offset
    return[x,y]

#takes a image tuple and returns the corresponding thermal tuple
def image_to_thermal( i_pixel):
    x, y = i_pixel
    x = (x - x_offset)/tc_horz_scale
    y = (y - y_offset)/tc_vert_scale
    return [x,y]

#takes the top left and bottoms right coordinates of a facial detection window
#and returns the temperature values from the thermal camera that are inside that windwo
def get_temps( top_left , bottom_right):
    temps = []
    
    top_left = image_to_thermal(top_left)
    bottom_right = image_to_thermal(bottom_right)
    x, y = top_left
    a, b = bottom_right
    
    x = int(round(x))
    m = int(round(x)) #baseline position of x
    y = int(round(y)) - 1
    a = int(round(a))
    b = int(round(b))
    
    rx = int(a - x)
    ry = int(b - y - 1)
    
    
    for i in range(0,ry):
        y = y + 1
        x = m
        for j in range(0,rx):
            if 0 <= x < 32 and 0 <= y < 24:
                temps.append(round(frame[x + y*32],1))
            else:
                temps.append(0)
            x = x + 1
    

    
    #print(temps[0])
            
    return temps

#gets the n number of maximum temperatures from the facial detection window
#that are at least above some threshold value
def get_n_max_temps( top_left , bottom_right, n):
    temps = get_temps(top_left , bottom_right)
    leng_temps = len(temps)
    num_rel_temps = 0
    rel_temps = []

    count = n
    #leng of temps array less than n - sends array without temperatures
    if n < leng_temps:
        max_temps = []
        #finds first n values greater some threshold value
        for i in range(0,leng_temps):
            if temps[i] > rel_temp and count > 0:
                max_temps.append(temps[i])
                count = count - 1

        
        if not max_temps:
            max_temps.append(0)
        
        #gets n max_temps
        max_temps.sort()
        for i in range(0,leng_temps):
            if temps[i] > rel_temp:
                num_rel_temps = num_rel_temps + 1
                rel_temps.append(temps[i])
                if temps[i] > max_temps[0]:
                    max_temps[0] = temps[i]
                    max_temps.sort()
            elif temps[i] == 0:
                max_temps = []
                num_rel_temps = -1
                leng__temps = -1
                break
        
        max_temps.sort()
        #number of temps found in facial window in max_temps[1] and number of relavent temps in max_temps[2]
        if max_temps:
            max_temps.insert(0,n) #3 index
        else:
            max_temps.insert(0,0)
        max_temps.insert(0,num_rel_temps) #2
        max_temps.insert(0,leng_temps) #1 
        return max_temps
    else:
        temps.insert(0,0)
        temps.insert(0,num_rel_temps)
        temps.insert(0,leng_temps)
        return temps

            
        
def create_thermal_image( r ):       
    ly_offset = y_offset - tc_vert_scale
    for h in range(24):
        lx_offset = x_offset
        ly_offset = ly_offset + tc_vert_scale
        y_end = ly_offset + tc_vert_scale
        for w in range(32):
            x_end = lx_offset + tc_horz_scale
            t = frame[h * 32 + w]
            if t < rel_temp:
                r[ly_offset: y_end, lx_offset: x_end] = (0)
            elif rel_temp <= t < 31:
                 r[ly_offset: y_end, lx_offset: x_end] = (255)
            elif 31 <= t < 32:
                 r[ly_offset: y_end, lx_offset: x_end] = (255)
            elif 32 <= t < 32.5:
                r[ly_offset: y_end, lx_offset: x_end] = (255)
            elif 32.5 <= t < 34:
                r[ly_offset: y_end, lx_offset: x_end] = (255)
            elif 34 <= t < 35:
                r[ly_offset: y_end, lx_offset: x_end] = (255)
            elif 35 <= t < 300:
                r[ly_offset: y_end, lx_offset: x_end] = (255)
                        
            lx_offset = lx_offset + tc_horz_scale
    
    return r


def weighted_average( temps ,index ):
    weighted_average = 0
    len_of_tuples = 0
    if temps:
        for i in range(0,len(temps)):
            len_of_tuples = len_of_tuples + len(temps[i]) - 4
        for i in range(0,len(temps)):
            weighted_average = weighted_average + temps[i][index] * ((len(temps[i]) - 4)/len_of_tuples) 
        return round(weighted_average, 2)
    else:
        return -1

