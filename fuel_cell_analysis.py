import numpy as np
import scipy.optimize as optimize
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

class FuelCellAnalysisApp:
    def __init__(self, master):
        self.master = master
        master.title("Basic Fuel Cell Analysis Application")
        master.state('zoomed')

        # Contador para identificar corridas
        self.run_counter = 0
        self.colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
        self.markers = ['o', 's', '^', 'v', 'D', 'p', '*', 'h', '+', 'x']

        # Frame para los parámetros de entrada
        input_frame = ttk.Frame(master, padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Etiquetas y entradas para parámetros
        ttk.Label(input_frame, text="Pressure (atm):").grid(row=0, column=0, sticky=tk.W)
        self.pressure_entry = ttk.Entry(input_frame)
        self.pressure_entry.grid(row=0, column=1)
        self.pressure_entry.insert(0, "1")

        ttk.Label(input_frame, text="Temperature (K):").grid(row=1, column=0, sticky=tk.W)
        self.temperature_entry = ttk.Entry(input_frame)
        self.temperature_entry.grid(row=1, column=1)
        self.temperature_entry.insert(0, "343")

        ttk.Label(input_frame, text="Electrode Thickness (µm):").grid(row=2, column=0, sticky=tk.W)
        self.electrode_thickness_entry = ttk.Entry(input_frame)
        self.electrode_thickness_entry.grid(row=2, column=1)
        self.electrode_thickness_entry.insert(0, "450")

        ttk.Label(input_frame, text="Membrane Thickness (µm):").grid(row=3, column=0, sticky=tk.W)
        self.membrane_thickness_entry = ttk.Entry(input_frame)
        self.membrane_thickness_entry.grid(row=3, column=1)
        self.membrane_thickness_entry.insert(0, "125")

        # Botones para generar gráficas
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2)
        
        ttk.Button(btn_frame, text="Add Graphs", command=self.generate_plots).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Clear Graphs", command=self.clear_plots).grid(row=0, column=1, padx=5)

        # Frame para las gráficas
        self.plot_frame = ttk.Frame(master, padding="10")
        self.plot_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.grid_rowconfigure(1, weight=1)
        master.grid_columnconfigure(0, weight=1)

        # Figura de matplotlib con tamaño grande
        plt.rcParams['figure.figsize'] = (20, 10)
        self.figure, self.ax1 = plt.subplots(dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def flood_equation(self, x, constants):
        PROD, Cdrag, P_A, X_W_I, R, T, t_A, D_HW, F, P_SAT, MW_N, rhod_N, D_WN = constants
        return 13.373 - 11 * (PROD/x - 1)/Cdrag - \
               ((0.043 + 17.18 * (P_A * (X_W_I - R * T * (PROD - x) * t_A / (P_A * D_HW * 2 * F)) / P_SAT) - 
                 39.85 * ((P_A * (X_W_I - R * T * (PROD - x) * t_A / (P_A * D_HW * 2 * F)) / P_SAT)**2) + 
                 36 * ((P_A * (X_W_I - R * T * (PROD - x) * t_A / (P_A * D_HW * 2 * F)) / P_SAT)**3)) - 
               11 * (PROD/x - 1)/Cdrag) * np.exp(x * Cdrag * MW_N * t_A / (22 * F * rhod_N * D_WN))

    def generate_plots(self):
        # Leer valores de entrada
        P = float(self.pressure_entry.get())
        T = float(self.temperature_entry.get())
        ETh = float(self.electrode_thickness_entry.get())
        MTh = float(self.membrane_thickness_entry.get())

        # Constantes y parámetros iniciales
        F = 96485
        R = 8.314
        Erev = 1.23
        iLeak = 0.0
        Cdrag = 2.5
        NoS = 100

        # Parámetros específicos
        P_A = P * 101325
        P_C = P * 101325
        t_A = ETh * 0.000001
        t_C = ETh * 0.000001
        t_M = MTh * 0.000001
        P_SAT = 0.307 * 101325
        X_H_I = 0.9
        X_O_IV = 0.19
        X_W_IV = 0.1
        D_HW = 1.49 * (10**(-5))
        D_OW = 2.95 * (10**(-6))
        alpha = 2.0
        i0_ref = 1
        MW_N = 1.0
        rhod_N = 1970
        
        # Cálculos previos
        iL = 4 * F * P_C * D_OW * X_O_IV / (R * T * t_C)
        D_WN = 1.3113 * (10**(-10)) * np.exp(2416 * (1/303 - 1/T))
        X_W_I = 1.0 - X_H_I
        X_N_IV = 1.0 - X_O_IV - X_W_IV
        X_W_III = P_SAT / P_C

        PROD = (X_W_III - X_W_IV) * P_C * D_OW * 2 * F / (R * T * t_C)
        constants = [PROD, Cdrag, P_A, X_W_I, R, T, t_A, D_HW, F, P_SAT, MW_N, rhod_N, D_WN]

        # Encontrar corriente de inundación
        iFlood = optimize.root(self.flood_equation, 1, args=(constants,)).x[0] * 10

        # Inicializar arrays
        CD = np.zeros(NoS + 1)
        etta_act = np.zeros(NoS + 1)
        V_cell = np.zeros(NoS + 1)

        # Bucle principal
        for j in range(NoS + 1):
            i = (j) * (1 - 1.e-6) * iL / NoS + iLeak
            CD[j] = i
            
            if (i/i0_ref) > 1:
                etta_act[j] = (R * T / (alpha * F)) * (np.log(i/i0_ref) - 
                               np.log(P_C * (X_O_IV - R * T * i * t_C / (4 * F * P_C * D_OW)) / 101325))
            else:
                etta_act[j] = 0.0
            
            V_cell[j] = Erev - etta_act[j]

        # Seleccionar color y marcador para la corrida
        color_voltaje = self.colors[self.run_counter % len(self.colors)]
        marker_voltaje = self.markers[self.run_counter % len(self.markers)]

        # Limpiar leyenda previa si es la primera corrida
        if self.run_counter == 0:
            self.ax1.clear()

        # Graficar
        label_voltaje = f'Voltage (P={P}atm, T={T}K)'
        
        self.ax1.plot(CD, V_cell, label=label_voltaje, color=color_voltaje, marker=marker_voltaje, 
                      linestyle='-', markersize=5, markevery=10)
        self.ax1.set_xlabel('Current Density (A/m²)')
        self.ax1.set_ylabel('Voltage (V)', color='black')
        
        plt.title('Fuel Cell Performance')
        plt.grid(True)
        
        # Actualizar leyenda
        self.ax1.legend(loc='center left', bbox_to_anchor=(1.05, 0.5))
        
        # Ajustar layout para mostrar leyenda completa
        plt.tight_layout(rect=[0, 0, 0.9, 1])
        
        # Actualizar gráfica en la interfaz
        self.canvas.draw()

        # Incrementar contador de corridas
        self.run_counter += 1

    def clear_plots(self):
        # Reiniciar contador de corridas
        self.run_counter = 0
        
        # Limpiar gráficas
        self.ax1.clear()
        
        # Restablecer etiquetas y título
        self.ax1.set_xlabel('Current Density (A/m²)')
        self.ax1.set_ylabel('Voltage (V)', color='black')
        plt.title('Fuel Cell Performance')
        plt.grid(True)
        
        # Ajustar layout
        plt.tight_layout(rect=[0, 0, 0.9, 1])
        
        # Actualizar gráfica
        self.canvas.draw()

def main():
    root = tk.Tk()
    app = FuelCellAnalysisApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()