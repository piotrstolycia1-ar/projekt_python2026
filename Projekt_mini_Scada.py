import sys
from dataclasses import dataclass
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QSlider, QLabel, QStackedWidget, QTextEdit, QFrame


#MODEL

@dataclass
class TankModel:
    name: str
    capacity_l: float
    volume_l: float
    temp_c: float  #średnia temperatura w zbiorniku

    def level(self) -> float:
        if self.capacity_l <= 0:
            return 0.0
        return max(0.0, min(1.0, self.volume_l / self.capacity_l))

    def add(self, dV: float, Tin: float) -> float:
        if dV <= 0:
            return 0.0
        free = self.capacity_l - self.volume_l
        added = min(dV, max(0.0, free))
        if added <= 0:
            return 0.0

        if self.volume_l <= 1e-9:
            self.temp_c = Tin
        else:
            self.temp_c = (self.volume_l * self.temp_c + added * Tin) / (self.volume_l + added)

        self.volume_l += added
        return added

    def remove(self, dV: float) -> float:
        if dV <= 0:
            return 0.0
        removed = min(dV, max(0.0, self.volume_l))
        self.volume_l -= removed
        return removed

    def is_empty(self) -> bool:
        return self.volume_l <= 0.1

    def is_full(self) -> bool:
        return self.volume_l >= self.capacity_l - 0.1


#WIDOK
class SnowflakeIcon:
    def __init__(self, x, y, size=18):
        self.x, self.y, self.size = x, y, size
        self.active = True

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def set_active(self, on: bool):
        self.active = on

    def draw(self, p: QPainter):
        if not self.active:
            return

        col = QColor(200, 230, 255)
        p.setPen(QPen(col, 3, Qt.SolidLine, Qt.RoundCap))

        s = self.size
        cx, cy = self.x, self.y

        #6 ramion (co 30°): poziome, pionowe i dwie przekątne
        lines = [
            (-s, 0,  s, 0),
            (0, -s, 0, s),
            (-s*0.7, -s*0.7,  s*0.7,  s*0.7),
            (-s*0.7,  s*0.7,  s*0.7, -s*0.7),
        ]

        #rysuj 4 linie
        for x1, y1, x2, y2 in lines:
            p.drawLine(int(cx + x1), int(cy + y1), int(cx + x2), int(cy + y2))

class Pipe:
    def __init__(self, points, thickness=10, color=Qt.gray):
        self.points = [QPointF(float(x), float(y)) for x, y in points]
        self.thickness = thickness
        self.pipe_color = QColor(color) if isinstance(color, QColor) else QColor(150, 150, 150)
        self.fluid_color = QColor(0, 180, 255)
        self.flowing = False

    def set_flow(self, flowing: bool):
        self.flowing = flowing

    def draw(self, p: QPainter):
        if len(self.points) < 2:
            return
        path = QPainterPath()
        path.moveTo(self.points[0])
        for pt in self.points[1:]:
            path.lineTo(pt)

        p.setPen(QPen(self.pipe_color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        if self.flowing:
            p.setPen(QPen(self.fluid_color, max(1, self.thickness - 4),
                          Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)


class HeaterIcon:
    def __init__(self, x, y, h=30):
        self.x, self.y, self.h = x, y, h
        self.power = 0.0

    def set_power(self, v: float):
        self.power = max(0.0, min(1.0, v))

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def draw(self, p: QPainter):
        col = QColor(255, 220, 0) if self.power > 0.05 else QColor(160, 160, 160)
        glow = QColor(255, 255, 200, int(40 + 170 * self.power))

        p.setPen(QPen(glow, 7))
        for dx in (-8, 0, 8):
            p.drawLine(int(self.x + dx), int(self.y - self.h/2), int(self.x + dx), int(self.y + self.h/2))

        p.setPen(QPen(col, 3))
        for dx in (-8, 0, 8):
            p.drawLine(int(self.x + dx), int(self.y - self.h/2), int(self.x + dx), int(self.y + self.h/2))


class TankView:
    def __init__(self, x, y, w, h, model: TankModel, heater: HeaterIcon | None = None, cooler: SnowflakeIcon | None = None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.model = model
        self.heater = heater
        self.cooler = cooler

    def left_center(self):
        return (self.x, self.y + self.h / 2)

    def right_center(self):
        return (self.x + self.w, self.y + self.h / 2)

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def draw(self, p: QPainter):
        lvl = self.model.level()
        if lvl > 0:
            hfill = self.h * lvl
            y0 = self.y + self.h - hfill
            # kolor zaczyna się zmieniać od 70°C, a mocno czerwony przy 90°C
            if self.model.temp_c < 70.0:
                t = 0.0
            elif self.model.temp_c > 90.0:
                t = 1.0
            else:
                t = (self.model.temp_c - 70.0) / 20.0  # 70→0, 90→1

            col = QColor(
                int(255 * t),  # czerwony
                int(80 * (1 - t)),  # zielony
                int(255 * (1 - t)),  # niebieski
                220
            )

            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRect(int(self.x + 3), int(y0), int(self.w - 6), int(hfill - 2))

        p.setPen(QPen(Qt.white, 3))
        p.setBrush(Qt.NoBrush)
        p.drawRect(int(self.x), int(self.y), int(self.w), int(self.h))

        if self.heater is not None:
            cx, cy = self.center()
            self.heater.set_pos(cx, cy)
            self.heater.draw(p)

        if self.cooler is not None:
            cx, cy = self.center()
            self.cooler.set_pos(cx, cy)
            self.cooler.draw(p)


        p.setPen(Qt.white)
        p.setFont(QFont("Arial", 10))
        p.drawText(int(self.x), int(self.y - 22), f"{self.model.name}")
        p.drawText(int(self.x), int(self.y - 6),
                   f"{self.model.volume_l:.0f}/{self.model.capacity_l:.0f} L  |  {self.model.temp_c:.1f}°C")


class PumpIcon:
    def __init__(self, x, y, r=16):
        self.x, self.y, self.r = x, y, r
        self.active = True

    def set_active(self, on: bool):
        self.active = on

    def draw(self, p: QPainter):
        col = QColor(0, 220, 0) if self.active else QColor(120, 120, 120)
        p.setPen(QPen(Qt.white, 2))
        p.setBrush(col)
        p.drawEllipse(QPointF(self.x, self.y), self.r, self.r)
        p.setBrush(QColor(255, 255, 255, 200))
        tri = [
            QPointF(self.x - 4, self.y - 7),
            QPointF(self.x - 4, self.y + 7),
            QPointF(self.x + 8, self.y),
        ]
        p.drawPolygon(*tri)

class InstallationPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent  #dostajemy dostęp do modeli i rysowania

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        #informacja o fazie
        p.setPen(Qt.white)
        p.setFont(QFont("Arial", 14, QFont.Bold))
        p.drawText(20, 30,
                   "FAZA: NAPEŁNIANIE 2 ZBIORNIKÓW" if self.parent.phase == "FILL"
                   else "FAZA: MIESZANIE (STERUJ SUWAKIEM)")

        for pp in self.parent.pipes:
            pp.draw(p)

        self.parent.pump_split.draw(p)
        self.parent.pump_cold_out.draw(p)
        self.parent.pump_hot_out.draw(p)

        self.parent.v_big.draw(p)
        self.parent.v_cold.draw(p)
        self.parent.v_hot.draw(p)
        self.parent.v_mix.draw(p)

class ReportsAlarmsPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        #proste “panele” jak na screenie
        self.setStyleSheet("""
            QLabel { color: white; }
            QFrame { border: 1px solid #555; border-radius: 3px; }
            QTextEdit { background: #1b1b1b; color: white; border: none; }
        """)

        #Ramka raporty
        self.frame_reports = QFrame(self)
        self.frame_reports.setGeometry(25, 70, 950, 260)

        self.lbl_reports_title = QLabel("Raporty", self.frame_reports)
        self.lbl_reports_title.move(10, 8)
        self.lbl_reports_title.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.txt_reports = QTextEdit(self.frame_reports)
        self.txt_reports.setReadOnly(True)
        self.txt_reports.setGeometry(10, 35, 930, 215)

        #Ramka alarmy
        self.frame_alarms = QFrame(self)
        self.frame_alarms.setGeometry(25, 350, 950, 230)

        self.lbl_alarms_title = QLabel("Alarmy", self.frame_alarms)
        self.lbl_alarms_title.move(10, 8)
        self.lbl_alarms_title.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.txt_alarms = QTextEdit(self.frame_alarms)
        self.txt_alarms.setReadOnly(True)
        self.txt_alarms.setGeometry(10, 35, 930, 185)

        #czcionka obu Alarmow i Raportow
        font = QFont("Arial", 11)
        self.txt_reports.setFont(font)
        self.txt_alarms.setFont(font)

    def refresh(self):
        #RAPORTY
        big = self.parent.big
        cold = self.parent.cold
        hot = self.parent.hot
        mix = self.parent.mix

        rep = []
        rep.append(f"Zbiornik główny: {big.volume_l:.0f}/{big.capacity_l:.0f} L, {big.temp_c:.1f}°C")
        rep.append(f"Zimny (0°C): {cold.volume_l:.0f}/{cold.capacity_l:.0f} L, {cold.temp_c:.1f}°C")
        rep.append(f"Gorący (100°C): {hot.volume_l:.0f}/{hot.capacity_l:.0f} L, {hot.temp_c:.1f}°C")
        rep.append(f"Mieszalnik: {mix.volume_l:.0f}/{mix.capacity_l:.0f} L, {mix.temp_c:.1f}°C")
        rep.append(f"Faza: {self.parent.phase}")
        rep.append(f"Kondycjonowanie: {self.parent.cold_heat_t:.1f}/10.0 s (zimny), {self.parent.hot_heat_t:.1f}/10.0 s (gorący)")

        self.txt_reports.setPlainText("\n".join(rep))

        #ALARMY
        alarms = []

        #alarmy temperatury mieszalnika
        if mix.volume_l > 0.1:  #dopiero jak coś tam jest
            if mix.temp_c < 10.0:
                alarms.append("⚠ Uwaga: lodowata woda w mieszalniku (T < 10°C).")
            if mix.temp_c > 70.0:
                alarms.append("⚠ Uwaga: grozi poparzenie w mieszalniku (T > 70°C).")

        #komunikat końcowy po napełnieniu
        if self.parent.mix_full_msg:
            alarms.append(self.parent.mix_full_msg)

        if not alarms:
            alarms_text = "• Brak alarmów."
        else:
            alarms_text = "\n".join(f"• {a}" for a in alarms)

        self.txt_alarms.setPlainText(alarms_text)



#APLIKACJA

class SymulacjaMieszania(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCADA: napełnij 2 zbiorniki, potem steruj miksowaniem")
        self.setFixedSize(1000, 620)
        self.setStyleSheet("background-color:#222;")

        #STRONY (stack)
        self.stack = QStackedWidget(self)
        self.stack.setGeometry(0, 0, 1000, 620)

        self.page_install = InstallationPage(self)
        self.page_reports = ReportsAlarmsPage(self)

        self.stack.addWidget(self.page_install)  # index 0
        self.stack.addWidget(self.page_reports)  # index 1

        #MINI MENU (prawy górny róg)
        self.btn_install = QPushButton("Instalacja", self)
        self.btn_reports = QPushButton("Raporty/Alarmy", self)

        #małe ikonki
        self.btn_install.setGeometry(760, 10, 110, 26)
        self.btn_reports.setGeometry(875, 10, 115, 26)

        self.btn_install.setStyleSheet("background-color:#444; color:white; font-size:13px;")
        self.btn_reports.setStyleSheet("background-color:#444; color:white; font-size:13px;")

        self.btn_install.clicked.connect(lambda: self.switch_page(0))
        self.btn_reports.clicked.connect(lambda: self.switch_page(1))

        #komunikat końcowy (po napełnieniu mieszalnika)
        self.mix_full_msg = ""

        #MODELE
        self.big = TankModel("Zbiornik główny", 200.0, 200.0, 20.0)
        self.cold = TankModel("Zimny (0°C)", 100.0, 0.0, 20.0)
        self.hot = TankModel("Gorący (100°C)", 100.0, 0.0, 20.0)
        self.mix = TankModel("Mieszalnik", 100.0, 0.0, 0.0)

        self.heater = HeaterIcon(0, 0, h=38)
        self.snowflake = SnowflakeIcon(0, 0, size=18)

        #WIDOKI
        self.v_big = TankView(70, 180, 120, 220, self.big)
        self.v_cold = TankView(420, 80, 100, 170, self.cold, cooler=self.snowflake)
        self.v_hot = TankView(420, 320, 100, 170, self.hot, heater=self.heater)
        self.v_mix = TankView(760, 200, 120, 220, self.mix)

        #POMPY
        self.pump_split = PumpIcon(300, 290, r=18)
        self.pump_cold_out = PumpIcon(660, 160, r=14)
        self.pump_hot_out = PumpIcon(660, 405, r=14)

        #RURY
        bx, by = self.v_big.right_center()
        cx_left, _ = self.v_cold.left_center()
        hx_left, _ = self.v_hot.left_center()
        mx, my = self.v_mix.left_center()

        self.pipe_big_to_pump = Pipe([(bx, by), (260, by), (280, 290)], thickness=10)

        self.pipe_pump_to_cold = Pipe([(320, 290), (360, 290), (360, 160), (cx_left, 160)], thickness=10)
        self.pipe_pump_to_hot = Pipe([(320, 290), (360, 290), (360, 405), (hx_left, 405)], thickness=10)

        self.pipe_cold_to_mix = Pipe([(self.v_cold.right_center()[0], 160), (660, 160), (700, 160), (700, my), (mx, my)], thickness=10)
        self.pipe_hot_to_mix = Pipe([(self.v_hot.right_center()[0], 405), (660, 405), (700, 405), (700, my), (mx, my)], thickness=10)

        self.pipes = [
            self.pipe_big_to_pump, self.pipe_pump_to_cold, self.pipe_pump_to_hot,
            self.pipe_cold_to_mix, self.pipe_hot_to_mix
        ]

        #STEROWANIE
        self.lbl_speed = QLabel("Szybkość pompy: 1.0 L/tick", self.page_install)
        self.lbl_speed.setStyleSheet("color:white;")
        self.lbl_speed.move(40, 560)

        self.sl_speed = QSlider(Qt.Horizontal, self.page_install)
        self.sl_speed.setGeometry(190, 560, 220, 20)
        self.sl_speed.setRange(1, 10)
        self.sl_speed.setValue(3)

        #ZIMNA -> MIX
        self.lbl_cold = QLabel("Zimna → mix: 0.0 L/tick", self.page_install)
        self.lbl_cold.setStyleSheet("color:white;")
        self.lbl_cold.move(440, 545)

        self.sl_cold = QSlider(Qt.Horizontal, self.page_install)
        self.sl_cold.setGeometry(640, 545, 220, 20)
        self.sl_cold.setRange(0, 5)  # 0.0 .. 5.0
        self.sl_cold.setValue(0)

        #CIEPŁA -> MIX (osobny suwak)
        self.lbl_hot = QLabel("Ciepła → mix: 0.0 L/tick", self.page_install)
        self.lbl_hot.setStyleSheet("color:white;")
        self.lbl_hot.move(440, 575)

        self.sl_hot = QSlider(Qt.Horizontal, self.page_install)
        self.sl_hot.setGeometry(640, 575, 220, 20)
        self.sl_hot.setRange(0, 5)  # 0.0 .. 5.0
        self.sl_hot.setValue(0)

        self.btn = QPushButton("Start / Stop", self.page_install)
        self.btn.setGeometry(880, 550, 100, 35)
        self.btn.setStyleSheet("background-color:#444; color:white;")
        self.btn.clicked.connect(self.toggle)

        self.btn_reset = QPushButton("RESET", self.page_install)
        self.btn_reset.setGeometry(880, 505, 100, 35)
        self.btn_reset.setStyleSheet("background-color:#444; color:white;")
        self.btn_reset.clicked.connect(self.reset_all)

        self.t_sim = 0.0
        self.cold_heat_t = 0.0
        self.hot_heat_t = 0.0
        self.cold_ready = False
        self.hot_ready = False

        #TRYB: najpierw FILL, potem MIX
        self.phase = "FILL"   # "FILL" albo "MIX"

        self.running = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.step)
        self.timer.start(30)

    def toggle(self):
        self.running = not self.running

    def reset_all(self):
        #stany
        self.phase = "FILL"
        self.t_sim = 0.0
        self.cold_heat_t = 0.0
        self.hot_heat_t = 0.0
        self.cold_ready = False
        self.hot_ready = False

        #zbiorniki
        self.big.volume_l = 200.0
        self.big.temp_c = 20.0

        self.cold.volume_l = 0.0
        self.cold.temp_c = 20.0

        self.hot.volume_l = 0.0
        self.hot.temp_c = 20.0

        self.mix.volume_l = 0.0
        self.mix.temp_c = 0.0

        #suwaki (startowo mało)
        self.sl_speed.setValue(3)  # np. 0.3 L/tick
        self.sl_cold.setValue(0)
        self.sl_hot.setValue(0)

        self.mix_full_msg = ""
        self.page_reports.refresh()
        self.page_install.update()

    def switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)

        #"podświetlenie” aktywnej zakładki
        if idx == 0:
            self.btn_install.setStyleSheet("background-color:#666; color:white; font-size:13px;")
            self.btn_reports.setStyleSheet("background-color:#444; color:white; font-size:13px;")
        else:
            self.btn_install.setStyleSheet("background-color:#444; color:white; font-size:13px;")
            self.btn_reports.setStyleSheet("background-color:#666; color:white; font-size:13px;")

    def cool_process(self, dt):
        target = 0.0
        #liniowo: w 10 s dochodzi do target (z grubsza)
        rate = (target - self.cold.temp_c) / 10.0
        self.cold.temp_c += rate * dt

    def heat_process(self, dt):
        target = 100.0
        rate = (target - self.hot.temp_c) / 10.0
        self.hot.temp_c += rate * dt

        #świecenie grzałki: moc ~ im dalej od 100
        self.heater.set_power(max(0.0, min(1.0, abs(target - self.hot.temp_c) / 60.0)))

    def step(self):
        pump_rate = self.sl_speed.value() / 10.0
        cold_rate = self.sl_cold.value() / 10.0  # L/tick
        hot_rate = self.sl_hot.value() / 10.0  # L/tick
        dt = 0.03  # bo timer masz 30 ms
        self.t_sim += dt

        self.lbl_cold.setText(f"Zimna → mix: {cold_rate:.1f} L/tick")
        self.lbl_hot.setText(f"Ciepła → mix: {hot_rate:.1f} L/tick")

        self.lbl_speed.setText(f"Szybkość pompy: {pump_rate:.1f} L/tick")

        if self.cold.volume_l > 0.1:
            self.cool_process(dt)

        if self.hot.volume_l > 0.1:
            self.heat_process(dt)
        else:
            self.heater.set_power(0.0)

        if not self.running:
            for pp in self.pipes:
                pp.set_flow(False)
            self.pump_split.set_active(False)
            self.pump_cold_out.set_active(False)
            self.pump_hot_out.set_active(False)
            self.heater.set_power(0.0)
            self.page_reports.refresh()
            self.page_install.update()

            return

        for pp in self.pipes:
            pp.set_flow(False)

        #PHASE 1: NAJPIERW NAPEŁNIJ COLD I HOT
        if self.phase == "FILL":
            self.pump_split.set_active(True)
            self.pump_cold_out.set_active(False)
            self.pump_hot_out.set_active(False)

            #Pompuj tylko do momentu, aż oba pełne
            if not (self.cold.is_full() and self.hot.is_full()) and not self.big.is_empty():
                take = self.big.remove(pump_rate)

                #rozdział 50/50, ale dociśnij do pełna
                to_cold = take * 0.5
                to_hot = take * 0.5

                added_c = self.cold.add(to_cold, self.big.temp_c)
                rest = to_cold - added_c
                if rest > 0:
                    self.hot.add(rest, self.big.temp_c)

                added_h = self.hot.add(to_hot, self.big.temp_c)
                rest2 = to_hot - added_h
                if rest2 > 0:
                    self.cold.add(rest2, self.big.temp_c)

                self.pipe_big_to_pump.set_flow(True)
                self.pipe_pump_to_cold.set_flow(True)
                self.pipe_pump_to_hot.set_flow(True)

            #gdy oba pełne -> przejdź do sterowania miksowaniem
            if self.cold.is_full() and self.hot.is_full():
                self.phase = "MIX"

            self.page_reports.refresh()
            self.page_install.update()

            return

        #liczymy tylko jeśli w zbiorniku jest woda i jeszcze nie jest gotowy
        if self.cold.volume_l > 0.1 and not self.cold_ready:
            self.cold_heat_t += dt
            if self.cold_heat_t >= 10.0:
                self.cold_ready = True

        if self.hot.volume_l > 0.1 and not self.hot_ready:
            self.hot_heat_t += dt
            if self.hot_heat_t >= 10.0:
                self.hot_ready = True

        #PHASE 2: Teraz sami sterujemy do mieszalnika
        self.pump_split.set_active(False)  #rozdział już nie pracuje
        self.pump_cold_out.set_active(False)
        self.pump_hot_out.set_active(False)

        if not self.mix.is_full():
            #tu zostaje Twoje nalewanie jak było
            cold_out = 0.0
            if not self.cold_ready:
                cold_out = 0.0
            else:
                cold_out = min(cold_rate, self.cold.volume_l)

            hot_out = 0.0
            if not self.hot_ready:
                hot_out = 0.0
            else:
                hot_out = min(hot_rate, self.hot.volume_l)

            removed_c = self.cold.remove(cold_out)
            if removed_c > 0:
                self.mix.add(removed_c, self.cold.temp_c)
                self.pipe_cold_to_mix.set_flow(True)
                self.pump_cold_out.set_active(True)

            removed_h = self.hot.remove(hot_out)
            if removed_h > 0:
                self.mix.add(removed_h, self.hot.temp_c)
                self.pipe_hot_to_mix.set_flow(True)
                self.pump_hot_out.set_active(True)

        else:
            #MIX pełny – ustaw komunikat raz
            if self.mix_full_msg == "":
                self.mix_full_msg = f"Otrzymano wyregulowaną temperaturę: {self.mix.temp_c:.1f}°C (mieszalnik pełny)."

        self.page_reports.refresh()
        self.page_install.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SymulacjaMieszania()
    w.show()
    sys.exit(app.exec_())
