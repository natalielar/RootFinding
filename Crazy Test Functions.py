import yroots as yr
import numpy as np

p20a = lambda x,y: 4*y**2*(4*y**2-a**2)-4*x**2*(4*x**2-1) #diabolic combination of devil's curves
p20b = lambda x,y: (4*(y**2)*(4*(y**2)-a(1))-4*(x**2)*(4*(x**2)-1))*(4*(y**2)*(4*(y**2)-a(2))-4*(x**2)*(4*(x**2)-1))*(4*(y**2)*(4*(y**2)-a(3))-4*(x**2)*(4*(x**2)-1))*(4*(y**2)*(4*(y**2)-a(end-1))-4*(x**2)*(4*(x**2)-1))*(4*(y**2)*(4*(y**2)-a(end))-4*(x**2)*(4*(x**2)-1))