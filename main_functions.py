#Contains the person object and all necessary functions except the Draw functions
import math
import board
import busio
import adafruit_mlx90640
import numpy as np
import threading


#mlx90640 i2c and camera object definitions from library
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ


#delineating temperature between possible face pixel and not face pixel
frame_count = 0
fever_message_timer = 0
obstruction_message_timer = 0
rel_temp = 32.5
ambient = 0
face_is_present = False
max_face_temp = 35
mutex_thermal = threading.Lock()



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
face_area = 254.88
forehead = 37.8*3
#camera factors: conventional camera FOV = 54x41; thermal camera FOV 55x35
#pi*[tan(angle1/2)*d]*[tan(angle2/2)*d] = FOV area at some distance
#or: pi*tan(angle1/2)*tan(angle2/2) * d^2 --> d^2 is the unknown ,the rest is just a constant factor 
cam_factor = math.pi*math.tan(math.radians(27))*math.tan(math.radians(20.5))
therm_factor = math.pi*math.tan(math.radians(27.5))*math.tan(math.radians(17.5))


#Example: 0.30 will shrink the thermal projection onto the camera image by 30%
x_offset_factor = 0.20 
y_offset_factor = 0.20
tc_horz_scale = int((h_res//32)*(1-x_offset_factor))
tc_vert_scale = int((v_res//24)*(1-y_offset_factor))

#moves the entire thermal projection on camera image up or down, by an integer number of thermal pixels
#moving axis without shrinking may cause a segmentation fault
y_axis = tc_vert_scale*3
x_axis = tc_horz_scale*0

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
        self.last_therm_x = last_therm_x
        self.last_therm_y = last_therm_y
        self.time_to_live = ttl
        self.temps = []
        self.frames = frams
        self.def_temp = t
        self.alive = False
        self.last_x = lastx
        self.last_y = lasty
        self.move_retry = 0
        self.total_temps = 0
        self.size = c
        self.sizes = []
        self.has_coffee = False
        self.coffee_ttl = 0
        self.obstruction_count = 5
        self.distance = 200
        self.w_distance = 0
        self.w_t_pixels = 0
        self.w_area = 0
        



frame = [0] * 768


    

    

def refresh_thermalCamera():
    global ambient
    global face_is_present
    global rel_temp
    while True:
        try:
            mutex_thermal.acquire()
            mlx.getFrame(frame)
            mutex_thermal.release()
        except ValueError:
            continue
        if frame and face_is_present == False and ambient > 0:
            mean = np.average(frame)
            std_dev = np.std(frame)
            num_temps = 0
            ambient_temp = 0
            for i in range(768):
                if mean - std_dev < frame[i] < std_dev + mean and frame[i] < 27.8:
                    ambient_temp = ambient_temp + frame[i]
                    num_temps = num_temps + 1
                if num_temps > 0:
                    ambient_temp = ambient_temp/num_temps
            if ambient - 1 < ambient_temp < ambient + 1 or ambient == 0:
                ambient = ambient_temp
                #print(ambient, rel_temp)
                
        elif frame and face_is_present == False and ambient == 0 and frame_count > 30:
            mean = np.average(frame)
            std_dev = np.std(frame)
            num_temps = 0
            ambient_temp = 0
            for i in range(768):
                if mean - std_dev < frame[i] < std_dev + mean and frame[i] < 27.8:
                    ambient_temp = ambient_temp + frame[i]
                    num_temps = num_temps + 1
            ambient_temp = ambient_temp/num_temps
            ambient = ambient_temp

                



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
def def_temp_calc( temps ):
    raw_temp = True
    correction = 0
    def_temp = 0
    #temps = [[distance][area_of_facial_detection_rectangle][number_of_likely_face_pixels][hot_temp1]...[..hottest_temp n]
    if len(temps) > 0:
        for i in range(0, len(temps)):
            correction = 0
            temp = 0
            #print('distance', round(temps[i][0]), "area",temps[i][1],"t_pixels", temps[i][2] ,"ratio", temps[i][2]/temps[i][1])
            for j in range(3,len(temps[i])):
                #print(" temps ",temps[i][j], end = "")
                temp = temp + temps[i][j]
            temp = temp/((len(temps[i]))-3)
            if raw_temp == False:
                
                correction = 0.0054*temps[i][0] - 2.5664*(temps[i][2]/temps[i][1]) + 3.1108
                def_temp = def_temp + temp + correction
            #print(" distance", temps[i][0]) #"correction ", correction, " def_temp", temp + correction)
            else:
                def_temp = def_temp + temp
    else:
        return 0
     
    def_temp = def_temp/len(temps)
    if def_temp < 35.0 and raw_temp == False:
        if temps[-1][0] < 80:
            def_temp = 3
        else:
            def_temp = 0
    #print("ave_temp", def_temp, "distance", temps[-1][0],"\n")
    
    return def_temp

#distance calculator
def distance( c ):
    #the face area is cm^2, so will return distance in cm
    ratio = c**2/total_pixels
    distance = (face_area/ratio)/cam_factor
    distance = math.sqrt(distance)
    
    return distance   
    
def num_max_temps( d ):
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
            
    return temps

#gets the n number of maximum temperatures from the facial detection window
#that are at least above some threshold value
def get_n_max_temps( top_left , bottom_right, n):
    temps = get_temps(top_left , bottom_right)
    leng_temps = len(temps)
    num_rel_temps = 0
    

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
        
        #gets 4 max_temps
        max_temps.sort()
        for i in range(0,leng_temps):
            if temps[i] > rel_temp:
                num_rel_temps = num_rel_temps + 1
                if temps[i] > max_temps[0]:
                    max_temps[0] = temps[i]
                    max_temps.sort()
            elif temps[i] == 0:
                max_temps = []
                num_rel_temps = -1
                leng__temps = -1
                break
        
        max_temps.sort()
        
        #number of temps found in facial window in max_temps[0] and number of relavent temps in max_temps[1]
        max_temps.insert(0,num_rel_temps)
        max_temps.insert(0,leng_temps)
        return max_temps
    else:
        temps.insert(0,num_rel_temps)
        temps.insert(0,leng_temps)
        return temps

            
        
def create_thermal_image( r ):       
    ly_offset = y_offset - tc_vert_scale
    for h in range(24):
        lx_offset = int(h_res*(x_offset_factor/2))
        ly_offset = ly_offset + tc_vert_scale
        y_end = ly_offset + tc_vert_scale
        for w in range(32):
            x_end = lx_offset + tc_horz_scale
            t = frame[h * 32 + w]
            if t < 30:
                r[ly_offset: y_end, lx_offset: x_end] = (0)
            elif 30 <= t < 31:
                 r[ly_offset: y_end, lx_offset: x_end] = (0)
            elif 31 <= t < 32:
                 r[ly_offset: y_end, lx_offset: x_end] = (255)
            elif rel_temp <= t < 32.5:
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
            len_of_tuples = len_of_tuples + len(temps[i]) - 3
        for i in range(0,len(temps)):
            weighted_average = weighted_average + temps[i][index] * ((len(temps[i]) - 3)/len_of_tuples) 
        return round(weighted_average, 2)
    else:
        return -1



    


    



