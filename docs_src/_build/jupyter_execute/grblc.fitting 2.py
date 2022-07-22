#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
from grblc.fitting import Model, Lightcurve

model = Model.W07(vary_t=False)
xdata = np.linspace(0, 10, 15)
yerr = np.random.normal(0, 0.5, len(xdata))
ydata = model(xdata, 5, -12, 1.5, 0) + yerr
lc = Lightcurve(xdata=xdata, ydata=ydata, yerr=yerr, model=model)
lc.show_data()


# In[2]:


import numpy as np
from grblc.fitting import Model, Lightcurve

model = Model.W07()
xdata = np.linspace(0, 10, 15)
yerr = np.random.normal(0, 0.5, len(xdata))
ydata = model(xdata, 5, -12, 1.5, 0) + yerr
lc = Lightcurve(xdata=xdata, ydata=ydata, yerr=yerr, model=model)
lc.fit(p0=[4.5, -12.5, 1, 0])
lc.show_fit(detailed=True)


# In[3]:


import matplotlib.pyplot as plt
import numpy as np
from grblc.fitting import Model

sbpl = Model.SIMPLE_BPL()
x = np.linspace(2, 8, 100)
T, F, alpha1, alpha2 = p = 5, -12, -0.1, 1.5
y = sbpl(x, *p)
plt.plot(x, y)
plt.title(sbpl.name)
plt.xlabel("log Time (s)")
plt.ylabel("log Flux (erg cm$^{-2}$ s$^{-1}$)")
plt.show()


# In[4]:


import matplotlib.pyplot as plt
import numpy as np
from grblc.fitting import Model
get_ipython().run_line_magic('matplotlib', 'inline')

sbpl = Model.SMOOTH_BPL()
x = np.linspace(2, 8, 100)
T, F, alpha1, alpha2, S = p = 5, -12, -0.1, 1.5, 0.5
y = sbpl(x, *p)
plt.plot(x, y)
plt.title(sbpl.name)
plt.xlabel("log Time (s)")
plt.ylabel("log Flux (erg cm\(^{-2}\) s\(^{-1}\))")
plt.show()


# In[5]:


import matplotlib.pyplot as plt
import numpy as np
from grblc.fitting import Model
get_ipython().run_line_magic('matplotlib', 'inline')

w07 = Model.W07()
x = np.linspace(2, 8, 100)
T, F, alpha, t = 5, -12, 1.5, 1
y = w07(x, T, F, alpha, t)
plt.plot(x, y)
plt.title(w07.name)
plt.xlabel("log Time (s)")
plt.ylabel("log Flux (erg cm$^{-2}$ s$^{-1}$)")
plt.show()

