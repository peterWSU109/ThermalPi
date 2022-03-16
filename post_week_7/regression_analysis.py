import os
import numpy as np
import math
import pandas as pd
from sklearn.linear_model import LinearRegression
import statsmodels.api as sm

#returns an array of all path names in a given directory

raw_temp_control = 30.5
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
file = file[file['def_temps'] > raw_temp_control]

    
df0 = file[['distance','ambient']].copy()
df0['distance_temp'] = file['distance'] * file['def_temps']
df0['std_dev_ratio'] = file['ratio']
df1 = pd.DataFrame(file["residuals"])



reg = LinearRegression().fit(df0,df1)
#Prints results
print("All raw_temps > ", raw_temp_control)  
print("r^2 = ", reg.score(df0,df1))
print("coeffecients", reg.coef_)
print("y-intercept", reg.intercept_)

#Significantly Faster than the reg.predict method, but tedious to rewrite
#distance_beta = reg.coef_[0][0]
#ratio_beta = reg.coef_[0][1]
#std_dev_beta = reg.coef_[0][2]
#ambient_beta = reg.coef_[0][3]
#y_intercept = reg.intercept_

#for row in file.index:
    #calc_temps.append(float(file['distance'][row] * distance_beta + file['ratio'][row] * ratio_beta + file['std_dev'][row] * std_dev_beta + file['ambient'][row] * ambient_beta + file['def_temps'][row] + y_intercept))
    #real_temps.append(float(file['def_temps'][row] + file['residuals'][row]))

for row in file.index:
    calc_temps.append(reg.predict(df0.loc[[row,]]) + file['def_temps'][row])
    real_temps.append(float(file['def_temps'][row] + file['residuals'][row]))

count = 0
total_temps = len(calc_temps)
for i in range(0,total_temps):
    if not (- 0.5 < calc_temps[i] - real_temps[i] <  0.5):
        count = count + 1
        
print("Temp statistics: number out of +/-0.5 celcius and percentage Out")
print("total temps: ", total_temps, "  Total temps OOR: ", count,  "  Percentage Out: ", count/total_temps)

df0 = sm.add_constant(df0)
ols = sm.OLS(df1, df0)
ols_result = ols.fit()
print(ols_result.summary())
    

