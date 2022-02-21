#Contains the person object and all necessary functions except the Draw functions
import math
import board
import busio
import adafruit_mlx90640
import numpy as np

#mlx90640 i2c and camera object definitions from library
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ


#delineating temperature between possible face pixel and not face pixel
frame_count = 0
rel_temp = 0
ambient = 0
face_is_present = False
max_face_temp = 34

#Touch Screen display is 800x480
#resolution of image for use by openCV
h_res = 320 #320,640,1024
v_res = 240 #240,480,768


#Example: 0.30 will shrink the thermal projection onto the camera image by 30%
x_offset_factor = 0.30 
y_offset_factor = 0.30
tc_horz_scale = int((h_res//32)*(1-x_offset_factor))
tc_vert_scale = int((v_res//24)*(1-y_offset_factor))

#moves the entire thermal projection on camera image up or down, by an integer number of thermal pixels
#moving axis without shrinking may cause a segmentation fault
y_axis = tc_vert_scale*5

x_offset = int(h_res*(x_offset_factor/2))
y_offset = int(v_res*(y_offset_factor/2)) - y_axis


#d_scale or distance scale gives a factor for how area changes with increased pixel resolution, 320x240 is default (=1)
d_scale = h_res*v_res//(320*240)
tc_horz_scale = int((h_res//32)*(1-x_offset_factor))
tc_vert_scale = int((v_res//24)*(1-y_offset_factor))

#person object contains all necessary data to keep track of a face and corresponding temperature while
#face is in FOV of at least the conventional camera
class person:
    def __init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, t = 0, c = 0):
        self.x = x_cor
        self.y = y_cor
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
        self.obstruction_count = 3



frame = [0] * 768

def refresh_thermalCamera():
    global ambient
    global face_is_present
    global rel_temp
    while True:
        try:
            mlx.getFrame(frame)
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
            ambient_temp = ambient_temp/num_temps
            if ambient - 0.5 < ambient_temp < ambient + 0.5 or ambient == 0:
                ambient = ambient_temp
                rel_temp = ambient + 7
                if rel_temp > 31:
                    rel_temp = 31
                #print(ambient, rel_temp)
        elif frame and face_is_present == False and ambient == 0 and frame_count > 30:
            mean = np.average(frame)
            std_dev = np.std(frame)
            num_temps = 0
            ambient_temp = 0
            if std_dev < 1.5:
                for i in range(768):
                    if mean - std_dev < frame[i] < std_dev + mean and frame[i] < 27.8:
                        ambient_temp = ambient_temp + frame[i]
                        num_temps = num_temps + 1
                ambient_temp = ambient_temp/num_temps
                ambient = ambient_temp
                rel_temp = ambient + 7
                if rel_temp > 31:
                    rel_temp = 31
                



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

# a pure debug function to display temperature data
def gather_data( temps):
    area_ratio = 0
    average_temp = 0
    average_area_ratio = 0
    average_average_temp = 0
    average_area = 0
      
    for i in range(0, len(temps)):
        #print(temps[i])
        area_ratio = ((temps[i][1])**0.5)/((temps[i][0])**0.5)
        average_area_ratio = average_area_ratio + area_ratio
        average_area = average_area + temps[i][0]
        #print(temps[i][2])
        #print(temps[i][0], temps[i][1])
        for j in range(2,len(temps[i])):
            average_temp = average_temp + temps[i][j]
        average_temp = average_temp/((len(temps[i]))-2)
        average_average_temp = average_average_temp + average_temp
        #print(temps[i][0],"area_ratio ", area_ratio, " average temp ", average_temp)
        average_temp = 0
    average_average_temp = average_average_temp/len(temps)
    average_area_ratio = average_area_ratio/len(temps)
    average_area = average_area/len(temps)
    print("ave area ", average_area, " ave ratio ", average_area_ratio, "ave temp ", average_average_temp, "frame", max(frame),"\n\n")
   

#calculates the Definitive temperature of a person
def def_temp_calc( temps ):
    global ambient
    ratio = 0
    area = 0
    def_temp = 0

    #temps = [[area_of_facial_detection_rectangle][number_of_likely_face_pixels][hottest_temp1]...[..temp4]
    if len(temps) > 0:
        for i in range(0, len(temps)):
            correction = 0
            temp = 0
            temp_x = 0

            #print("area",temps[i][0],"t_pixels", temps[i][1] ,"ratio", temps[i][1]/temps[i][0],end = "")
            for j in range(2,len(temps[i])):
                #print(" temps ",temps[i][j], end = "")
                temp = temp + temps[i][j]
            temp = temp/((len(temps[i]))-2)
            
            #calculates the correction to the average of the 40 hottest facial pixels based
            #on the number_of_likely_face_pixels found in the facial detection window
            
            #The below ranges and constants are hand calibrated based on testing
            
            #calculates x value to be put into correction function
            # 1 - sqrt(number_of_likely_face_pixels)/constant
            if temps[i][1] <= 100:
                temp_x = 1 - math.sqrt(temps[i][1])/19
            elif 100 < temps[i][1]<= 160:
                temp_x = 1 - math.sqrt(temps[i][1])/13.5
            elif 160 < temps[i][1]<= 225:
                temp_x = 1 - math.sqrt(temps[i][1])/15.5
            elif 225 < temps[i][1] <= 275:
                temp_x = 1 - math.sqrt(temps[i][1])/17
            elif 275 < temps[i][1] <= 325:
                temp_x = 1 - math.sqrt(temps[i][1])/19
            elif 325 < temps[i][1] <= 375:
                temp_x = 1 - math.sqrt(temps[i][1])/21
        
            #its a cubic,the correction changes alot from 0.25 to ~1.25 feet
            #Stays about the same to from 1.25 to 2.5 feet and then increases alot from
            #2.5 feet to 4.5/5 feet - beyond that - was unable to reliably calculate a core temp
            correction = 1.6 + ((3*temp_x) - 1.25)**3
            correction = correction + 0.11*(28.0 - ambient)
            
             
            #print("  correction ", correction, " def_temp", temp + correction, "max", max(frame))
            def_temp = def_temp + temp + correction
    else:
        return 32.5
              
    def_temp = def_temp/len(temps)
    #print("def_temp", def_temp, "\n")
    
    return def_temp
        
                                    
    
    
            
    

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
        #finds first 4 values greater some threshold value
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
                 r[ly_offset: y_end, lx_offset: x_end] = (0)
            elif 32 <= t < 32.5:
                r[ly_offset: y_end, lx_offset: x_end] = (0)
            elif 32.5 <= t < 34:
                r[ly_offset: y_end, lx_offset: x_end] = (160)
            elif 34 <= t < 35:
                r[ly_offset: y_end, lx_offset: x_end] = (200)
            elif 35 <= t < 300:
                r[ly_offset: y_end, lx_offset: x_end] = (255)
                        
            lx_offset = lx_offset + tc_horz_scale
    
    return r

    



