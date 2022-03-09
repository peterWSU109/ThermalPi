import os
import numpy as np
import math
import pandas as pd
from sklearn.linear_model import LinearRegression

#returns an array of all path names in a given directory

distance_control = True


real_temps = []
calc_temps = []
dfs = []
files = os.listdir("data")
if distance_control == True:
    for file in files:
        if file.find("_d_yes") > -1:
            dfs.append(pd.read_pickle("data/" + file))
else:
    for file in files:
        dfs.append(pd.read_pickle("data/" + file))

for i in range(1,len(dfs)):
    dfs[0] = pd.concat([dfs[0], dfs[i]], axis = 0, ignore_index = True)
    
    
    
        
file = dfs[0]

df0 = file[['distance','ratio','std_dev','ambient']].copy()
df1 = pd.DataFrame(file["residuals"])


reg = LinearRegression().fit(df0,df1)
#Prints results
print("r^2 = ", reg.score(df0,df1))
print("coeffecients", reg.coef_)
print("y-intercept", reg.intercept_)

distance_beta = reg.coef_[0][0]
ratio_beta = reg.coef_[0][1]
std_dev_beta = reg.coef_[0][2]
ambient_beta = reg.coef_[0][3]
y_intercept = reg.intercept_

for row in file.index:
    calc_temps.append(float(file['distance'][row] * distance_beta + file['ratio'][row] * ratio_beta + file['std_dev'][row] * std_dev_beta + file['ambient'][row] * ambient_beta + file['def_temps'][row] + y_intercept))
    real_temps.append(float(file['def_temps'][row] + file['residuals'][row]))

count = 0
total_temps = len(calc_temps)
for i in range(0,total_temps):
    if not (- 0.5 < calc_temps[i] - real_temps[i] <  0.5):
        count = count + 1
        
print("total temps: ", count, "Percentage Out: ", count/total_temps)
    
