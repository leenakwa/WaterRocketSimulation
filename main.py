import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.patches import Rectangle, Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
from PIL import Image

# Физические константы
g = 9.81  # ускорение свободного падения, м/с^2
rho_air = 1.225  # плотность воздуха, кг/м^3
rho_water = 1000  # плотность воды, кг/м^3
C_d = 0.5  # коэффициент лобового сопротивления
A = 0.008  # площадь сечения ракеты, м^2
A_t = 0.0001  # площадь сопла, м^2
m_empty = 0.15  # масса пустой ракеты, кг
P_atm = 101325  # атмосферное давление, Па
V_bottle = 0.002  # объём бутылки, м^3 (2 литра)
gamma = 1.4  # показатель адиабаты для воздуха
R_specific = 287  # удельная газовая постоянная для воздуха, Дж/(кг·К)
T0 = 300  # начальная температура воздуха в Кельвинах

class WaterRocket:
    def __init__(self, P0, V_water0):
        self.P0 = P0  # Начальное давление
        self.V_water0 = V_water0  # Начальный объём воды
        self.reset()

    def reset(self):
        self.t = 0  # время
        self.dt = 0.005  # шаг времени
        self.y = 0  # высота
        self.v = 0  # скорость
        self.a = 0  # ускорение
        self.V_air0 = V_bottle - self.V_water0  # Начальный объём воздуха
        self.V_air = self.V_air0
        self.V_water = self.V_water0
        self.m = m_empty + self.V_water * rho_water  # Начальная масса
        self.P = self.P0
        self.T = T0
        self.phase = 'water'  # Текущая фаза полёта: 'water', 'air', 'coasting'
        self.data = {'t': [], 'y': [], 'v': [], 'a': [], 'water_level': []}

    def step(self):
        if self.phase == 'water':
            # Фаза выброса воды
            if self.V_water > 0:
                # Вычисляем скорость истечения воды
                v_e = np.sqrt(2 * (self.P - P_atm) / rho_water)
                # Расход массы
                dm_dt = -rho_water * A_t * v_e
                # Тяга
                F_thrust = v_e * -dm_dt
                # Давление уменьшается по закону адиабаты
                self.V_air = V_bottle - self.V_water
                self.P = self.P0 * (self.V_air0 / self.V_air) ** gamma
                # Обновляем объём воды
                self.V_water += (dm_dt / rho_water) * self.dt
                # Обновляем массу
                self.m += dm_dt * self.dt
            else:
                # Переход к фазе выброса воздуха
                self.phase = 'air'
                F_thrust = 0
        elif self.phase == 'air':
            # Фаза выброса воздуха
            if self.P > P_atm:
                # Давление и температура газа
                P_exit = self.P
                T_exit = self.T * (P_exit / self.P0) ** ((gamma - 1) / gamma)
                # Скорость истечения воздуха
                v_e = np.sqrt(2 * gamma * R_specific * T_exit / (gamma - 1) * (1 - (P_atm / P_exit) ** ((gamma - 1) / gamma)))
                # Расход массы
                rho_exit = P_exit / (R_specific * T_exit)
                dm_dt = -A_t * rho_exit * v_e
                # Тяга
                F_thrust = v_e * -dm_dt + (P_exit - P_atm) * A_t
                # Обновляем давление и температуру
                self.V_air += A_t * v_e * self.dt
                self.P = self.P0 * (self.V_air0 / self.V_air) ** gamma
                self.T = T0 * (self.P / self.P0) ** ((gamma - 1) / gamma)
                # Обновляем массу
                self.m += dm_dt * self.dt
            else:
                # Переход к фазе свободного полёта
                self.phase = 'coasting'
                F_thrust = 0
        else:
            # Фаза свободного полёта
            F_thrust = 0

        # Сила сопротивления воздуха
        F_drag = 0.5 * rho_air * self.v**2 * C_d * A * np.sign(-self.v)

        # Суммарная сила
        F_net = F_thrust - self.m * g - F_drag

        # Ускорение
        self.a = F_net / self.m

        # Обновляем скорость и позицию
        self.v += self.a * self.dt
        self.y += self.v * self.dt

        # Обновляем время
        self.t += self.dt

        # Сохраняем данные для графика
        self.data['t'].append(self.t)
        self.data['y'].append(self.y)
        self.data['v'].append(self.v)
        self.data['a'].append(self.a)

        # Уровень воды в процентах
        water_level_percent = max(self.V_water, 0) / self.V_water0 * 100 if self.V_water0 > 0 else 0
        self.data['water_level'].append(water_level_percent)

    def run(self):
        while self.y >= 0 or self.v > 0:
            self.step()

class App:
    def __init__(self, master):
        self.master = master
        master.title("Модель водяной ракеты")

        # Параметры по умолчанию
        self.P0 = tk.DoubleVar(value=300000)  # Начальное давление, Па
        self.volume_value = tk.DoubleVar(value=1)  # Значение объёма воды (1 литр)
        self.volume_unit = tk.StringVar(value="Литры")  # Единицы измерения объёма

        # Создание элементов интерфейса
        tk.Label(master, text="Начальное давление (Па):").grid(row=0, column=0, sticky='e')
        tk.Entry(master, textvariable=self.P0).grid(row=0, column=1)

        tk.Label(master, text="Объём воды:").grid(row=1, column=0, sticky='e')
        tk.Entry(master, textvariable=self.volume_value).grid(row=1, column=1)

        self.unit_option = tk.OptionMenu(master, self.volume_unit, "Литры", "Проценты")
        self.unit_option.grid(row=1, column=2)

        self.start_button = tk.Button(master, text="Запустить модель", command=self.start_simulation)
        self.start_button.grid(row=2, column=0, columnspan=3)

        # Создание области для графика с использованием GridSpec
        self.figure = plt.Figure(figsize=(8, 8))
        gs = GridSpec(1, 2, figure=self.figure, width_ratios=[3, 1])

        self.ax_rocket = self.figure.add_subplot(gs[0])
        self.ax_progress = self.figure.add_subplot(gs[1])

        self.canvas = FigureCanvasTkAgg(self.figure, master)
        self.canvas.get_tk_widget().grid(row=3, column=0, columnspan=3)

    def start_simulation(self):
        # Очистка предыдущих графиков
        self.ax_rocket.clear()
        self.ax_progress.clear()

        # Получаем объём воды в м^3
        volume_input = self.volume_value.get()
        if self.volume_unit.get() == "Литры":
            V_water0 = volume_input / 1000  # Переводим в м^3
        else:  # Проценты
            V_water0 = (volume_input / 100) * V_bottle

        # Проверяем, чтобы объём не превышал объём бутылки
        if V_water0 > V_bottle:
            V_water0 = V_bottle

        # Создание объекта ракеты
        rocket = WaterRocket(self.P0.get(), V_water0)
        rocket.run()

        # Анимация полёта
        y_data = rocket.data['y']
        t_data = rocket.data['t']
        v_data = rocket.data['v']
        a_data = rocket.data['a']
        water_levels = rocket.data['water_level']

        # Настройка графика ракеты
        self.ax_rocket.set_xlim(-0.3, 0.3)
        self.ax_rocket.set_ylim(0, max(y_data) + 5)
        self.ax_rocket.set_xlabel('Ширина', fontsize=12)
        self.ax_rocket.set_ylabel('Высота (м)', fontsize=12)
        self.ax_rocket.set_title('Анимация полёта водяной ракеты', fontsize=14)

        # Создаем объекты для анимации ракеты
        rocket_body = Rectangle((-0.05, 0), 0.1, 0.8, fc='grey', ec='black')
        cone = Polygon([[-0.05, 0.8], [0, 1.1], [0.05, 0.8]], fc='red', ec='black')
        fin1 = Polygon([[-0.05, 0.2], [-0.1, 0], [-0.05, 0]], fc='green', ec='black')
        fin2 = Polygon([[0.05, 0.2], [0.1, 0], [0.05, 0]], fc='green', ec='black')
        self.ax_rocket.add_patch(rocket_body)
        self.ax_rocket.add_patch(cone)
        self.ax_rocket.add_patch(fin1)
        self.ax_rocket.add_patch(fin2)

        # Фиксация соотношения сторон
        self.ax_rocket.set_aspect('equal')

        # Настройка прогресс-бара уровня воды
        self.ax_progress.set_xlim(0, 1)
        self.ax_progress.set_ylim(0, 100)
        self.ax_progress.set_title('Уровень воды', fontsize=14)
        self.ax_progress.axis('off')

        # Создаем прямоугольник прогресс-бара
        progress_bar_outline = Rectangle((0.4, 0), 0.2, 100, fill=False, ec='black', lw=2)
        self.ax_progress.add_patch(progress_bar_outline)
        progress_bar_fill = Rectangle((0.4, 0), 0.2, 0, fc='blue', ec='blue')
        self.ax_progress.add_patch(progress_bar_fill)

        # Текстовое отображение уровня воды
        water_level_text = self.ax_progress.text(0.5, -10, '', ha='center', fontsize=12)

        # Установка отступов
        self.figure.tight_layout()

        # Функция для обновления анимации
        def animate(i):
            # Обновляем положение ракеты
            y_pos = y_data[i]
            rocket_body.set_y(y_pos)
            cone_xy = [[-0.05, y_pos + 0.8], [0, y_pos + 1.1], [0.05, y_pos + 0.8]]
            cone.set_xy(cone_xy)
            fin1_xy = [[-0.05, y_pos + 0.2], [-0.1, y_pos], [-0.05, y_pos]]
            fin1.set_xy(fin1_xy)
            fin2_xy = [[0.05, y_pos + 0.2], [0.1, y_pos], [0.05, y_pos]]
            fin2.set_xy(fin2_xy)

            # Обновляем прогресс-бар уровня воды
            water_level_percent = water_levels[i]
            progress_bar_fill.set_height(water_level_percent)
            water_level_text.set_text(f"{int(water_level_percent)}%")

            return rocket_body, cone, fin1, fin2, progress_bar_fill, water_level_text

        # Создание анимации
        self.ani = animation.FuncAnimation(self.figure, animate, frames=len(t_data), interval=20, blit=True)

        self.canvas.draw()

        # Сохранение анимации в GIF
        self.save_animation()

        # Отображение графиков после завершения анимации
        self.show_plots(t_data, y_data, v_data, a_data)

    def save_animation(self):
        # Спрашиваем пользователя, хочет ли он сохранить анимацию
        save_gif = messagebox.askyesno("Сохранение GIF", "Вы хотите сохранить анимацию полёта ракеты в GIF-файл?")
        if save_gif:
            # Открываем диалоговое окно для выбора имени файла
            file_path = filedialog.asksaveasfilename(defaultextension='.gif', filetypes=[("GIF файлы", "*.gif")])
            if file_path:
                try:
                    # Сохраняем анимацию
                    self.ani.save(file_path, writer='pillow', fps=30)
                    messagebox.showinfo("Сохранение GIF", f"Анимация успешно сохранена в файл:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("Ошибка сохранения", f"Произошла ошибка при сохранении GIF:\n{e}")

    def show_plots(self, t_data, y_data, v_data, a_data):
        # Спрашиваем пользователя, хочет ли он посмотреть графики
        show_graphs = messagebox.askyesno("Графики полёта", "Вы хотите отобразить графики высоты, скорости и ускорения?")
        if not show_graphs:
            return

        # Создание нового окна для графиков
        fig_plots, axs = plt.subplots(3, 1, figsize=(8, 10))
        fig_plots.suptitle('Графики полёта ракеты', fontsize=16)

        # График высоты от времени
        axs[0].plot(t_data, y_data)
        axs[0].set_ylabel('Высота (м)', fontsize=12)
        axs[0].grid(True)

        # График скорости от времени
        axs[1].plot(t_data, v_data)
        axs[1].set_ylabel('Скорость (м/с)', fontsize=12)
        axs[1].grid(True)

        # График ускорения от времени
        axs[2].plot(t_data, a_data)
        axs[2].set_xlabel('Время (с)', fontsize=12)
        axs[2].set_ylabel('Ускорение (м/с²)', fontsize=12)
        axs[2].grid(True)

        # Настройка отступов
        plt.tight_layout()
        plt.show()

root = tk.Tk()
app = App(root)
root.mainloop()
