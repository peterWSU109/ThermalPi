
import time
import board
import busio as io
import adafruit_mlx90614


i2c = io.I2C(board.SCL, board.SDA, frequency=100000)
mlx = adafruit_mlx90614.MLX90614(i2c)

ambientString = "{:.2f}".format(mlx.ambient_temperature)
objectString = "{:.2f}".format(mlx.object_temperature)

time.sleep(1)
print("Ambient Temp: {} °C", ambientString)
print("Body Temp: {} °C",objectString)
