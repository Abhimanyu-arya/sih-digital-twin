import numpy as np
import matplotlib.pyplot as plt
import os

true_rul = np.linspace(0, 1200, 1000)
log_rul = np.log1p(true_rul)

fig, ax1 = plt.subplots(figsize=(8, 5))

color = 'tab:blue'
ax1.set_xlabel('Time to Failure (True RUL, seconds)')
ax1.set_ylabel('True RUL', color=color)
ax1.plot(true_rul, true_rul, color=color, label='True RUL (Linear)')
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()  
color = 'tab:red'
ax2.set_ylabel('log(1 + True RUL)', color=color)
ax2.plot(true_rul, log_rul, color=color, label='log(1 + RUL) Target')
ax2.tick_params(axis='y', labelcolor=color)

fig.tight_layout()
plt.title("Effect of log(1+RUL) Target Compression")
fig.legend(loc="upper left", bbox_to_anchor=(0.15,0.85))

output_path = r"C:\Users\jayhi\.gemini\antigravity-ide\brain\1c42e8dd-d8c1-427a-ae46-e71868c6f84c\log_compression_plot.png"
plt.savefig(output_path)
print("Saved plot to", output_path)
