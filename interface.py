import sys
import collections
import serial
import serial.tools.list_ports
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel, QPushButton,
                             QDoubleSpinBox, QSlider, QFrame, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

# --- THREAD DE COMMUNICATION SÉRIE ---
class MotorWorkerThread(QThread):
    data_updated = pyqtSignal(dict)
    connection_error = pyqtSignal(str)

    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self._keep_running = True
        self.serial_conn = None
        self.is_running = False

    def run(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Connecté avec succès à {self.port}")

            while self._keep_running:
                if self.serial_conn.in_waiting > 0:
                    ligne = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()

                    if ligne and ligne.startswith("ADC:"):
                        try:
                            # Exemple reçu : ADC:1023  Tension:0.82V  PWM:524  Vitesse:450 RPM
                            part_adc = ligne.split("ADC:")[1].split()[0]
                            part_tension = ligne.split("Tension:")[1].split("V")[0]
                            part_pwm = ligne.split("PWM:")[1].split()[0]
                            part_vitesse = ligne.split("Vitesse:")[1].split()[0]

                            donnees = {
                                'adc': int(part_adc),
                                'tension': float(part_tension),
                                'pwm': int(part_pwm),
                                'vitesse': float(part_vitesse)
                            }
                            self.data_updated.emit(donnees)

                        except Exception as e:
                            pass # Ignorer les erreurs d'analyse silencieusement

        except serial.SerialException as e:
            self.connection_error.emit(f"Erreur d'ouverture du port {self.port}: {e}")

        finally:
             if self.serial_conn and self.serial_conn.is_open:
                 self.serial_conn.close()

    def stop(self):
        self._keep_running = False
        self.wait()

    def send_command(self, cmd_str):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write((cmd_str + '\n').encode('utf-8'))
            except Exception as e:
                print(f"Erreur d'envoi : {e}")

    def set_running(self, state):
        self.is_running = state
        self.send_command("START" if state else "STOP")

    def set_direction(self, direction_str):
        self.send_command(f"DIR:{direction_str}")

    def set_target_speed(self, speed):
        self.send_command(f"SPEED:{int(speed)}")



import time
import random

class VirtualMotorWorkerThread(QThread):
    data_updated = pyqtSignal(dict)
    connection_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._keep_running = True
        self.is_running = False
        self.target_speed = 150
        self.current_speed = 0.0
        self.direction = 1 # 1 = droite, -1 = gauche
        self.direction_pending = False
        self.direction_change_start_time = 0

    def run(self):
        print("Connecté avec succès au Moteur Virtuel (Simulation)")
        while self._keep_running:
            # --- Logique de simulation physique ---
            if self.direction_pending:
                # Mode freinage avant changement de sens
                self.current_speed *= 0.8
                if time.time() - self.direction_change_start_time > 0.5:
                    self.direction_pending = False
            else:
                # Cible réelle prenant en compte le sens et l'état
                cible = self.target_speed * self.direction if self.is_running else 0

                # Inertie du moteur (filtre passe-bas)
                self.current_speed += (cible - self.current_speed) * 0.1

                # Bruit de mesure
                if abs(self.current_speed) > 5:
                    self.current_speed += random.uniform(-10, 10)

            # --- Génération des fausses données ---
            vitesse_rpm = int(self.current_speed)
            pwm_val = int((abs(vitesse_rpm) * 2099) / 4000)
            tension_simulee = 3.3 * (abs(self.target_speed) / 4000.0) if self.is_running else 0.0
            tension_simulee += random.uniform(0.0, 0.05) # Bruit ADC
            adc_val = int((tension_simulee / 3.3) * 4095)

            donnees = {
                'adc': adc_val,
                'tension': tension_simulee,
                'pwm': pwm_val,
                'vitesse': vitesse_rpm
            }

            self.data_updated.emit(donnees)
            time.sleep(0.1) # Boucle toutes les 100ms comme le STM32

    def stop(self):
        self._keep_running = False
        self.wait()

    def set_running(self, state):
        self.is_running = state

    def set_direction(self, direction_str):
        new_dir = 1 if direction_str == "DROITE" else -1
        if new_dir != self.direction:
            self.direction = new_dir
            self.direction_pending = True
            self.direction_change_start_time = time.time()

    def set_target_speed(self, speed):
        self.target_speed = speed


# --- STYLESHEET GLOBAL ---
QSS_STYLESHEET = """
QMainWindow { background-color: #12151C; color: #E0E6ED; font-family: 'Segoe UI', Arial, sans-serif; }
#main_title { color: #FFFFFF; font-size: 24px; font-weight: bold; letter-spacing: 2px; }

/* Cartes de valeurs (Cards) */
.ValueCard { background-color: #1A1F29; border-radius: 12px; border: 1px solid #2A3142; }
.CardTitle { color: #8A9BB3; font-size: 13px; font-weight: bold; text-transform: uppercase; }
.CardValue { color: #00D2FF; font-size: 32px; font-weight: bold; }
.CardUnit { color: #8A9BB3; font-size: 14px; font-weight: bold; margin-bottom: 5px;}

/* Panneaux de contrôle */
.ControlPanel { background-color: #1A1F29; border-radius: 12px; border: 1px solid #2A3142; padding: 15px; }

/* Boutons classiques */
QPushButton { background-color: #2A3142; color: white; border: none; border-radius: 6px; padding: 10px 15px; font-weight: bold; font-size: 13px;}
QPushButton:hover { background-color: #374158; }
QPushButton:disabled { background-color: #161A22; color: #4B5563; }

/* Bouton Connecter */
#connect_btn { background-color: #00D2FF; color: #12151C; }
#connect_btn:hover { background-color: #33DBFF; }
#connect_btn:checked { background-color: #FF3B30; color: white; }
#connect_btn:checked:hover { background-color: #FF5A52; }

/* Bouton Démarrer */
#start_btn { background-color: #10B981; color: white; font-size: 16px; padding: 15px; }
#start_btn:hover { background-color: #34D399; }
#start_btn:checked { background-color: #EF4444; }
#start_btn:checked:hover { background-color: #F87171; }

/* Boutons de Direction (Toggle) */
#dir_btn { background-color: #1A1F29; color: #8A9BB3; border: 2px solid #2A3142; }
#dir_btn:hover { background-color: #242B38; }
#dir_btn:checked { background-color: #242B38; color: #00D2FF; border: 2px solid #00D2FF; }

/* ComboBox et Inputs */
QComboBox { background-color: #2A3142; color: white; border: 1px solid #374158; border-radius: 6px; padding: 8px; font-size: 14px; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #1A1F29; color: white; selection-background-color: #2A3142; }

QDoubleSpinBox { background-color: #1A1F29; color: #00D2FF; border: 2px solid #2A3142; border-radius: 6px; padding: 10px; font-size: 20px; font-weight: bold; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; } /* Hide arrows */

QSlider::groove:horizontal { border: none; height: 8px; background: #2A3142; border-radius: 4px; }
QSlider::sub-page:horizontal { background: #00D2FF; border-radius: 4px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 2px solid #00D2FF; width: 20px; height: 20px; margin: -6px 0; border-radius: 10px; }
"""

# --- WIDGET CARTE DE VALEUR (CARD) ---
class ValueCard(QFrame):
    def __init__(self, title, unit, color="#00D2FF"):
        super().__init__()
        self.setProperty("class", "ValueCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")
        layout.addWidget(self.title_label)

        value_layout = QHBoxLayout()
        self.value_label = QLabel("0")
        self.value_label.setProperty("class", "CardValue")
        self.value_label.setStyleSheet(f"color: {color};")

        self.unit_label = QLabel(unit)
        self.unit_label.setProperty("class", "CardUnit")

        value_layout.addWidget(self.value_label, alignment=Qt.AlignmentFlag.AlignBottom)
        value_layout.addWidget(self.unit_label, alignment=Qt.AlignmentFlag.AlignBottom)
        value_layout.addStretch()
        layout.addLayout(value_layout)

    def set_value(self, value_str):
        self.value_label.setText(value_str)


# --- FENÊTRE PRINCIPALE (DASHBOARD) ---
class ModernMotorHMI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Motor Dashboard PRO")
        self.resize(1200, 800)
        self.setStyleSheet(QSS_STYLESHEET)

        self.worker = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # ================= HEADER =================
        header_layout = QHBoxLayout()

        title_label = QLabel("STM32 MOTOR DASHBOARD")
        title_label.setObjectName("main_title")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Selection du port COM
        self.port_combo = QComboBox()
        self.port_combo.setFixedWidth(150)
        self.refresh_ports()
        header_layout.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        header_layout.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("CONNECTER")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.setCheckable(True)
        self.connect_btn.setFixedWidth(120)
        self.connect_btn.clicked.connect(self.toggle_connection)
        header_layout.addWidget(self.connect_btn)

        main_layout.addLayout(header_layout)

        # ================= TOP SECTION (CARDS & CONTROLS) =================
        top_section = QHBoxLayout()

        # --- CARDS (Left) ---
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(15)

        self.card_vitesse = ValueCard("VITESSE RÉELLE MOTEUR", "RPM", color="#00D2FF")
        self.card_pwm = ValueCard("DUTY CYCLE (PWM)", "/ 2099", color="#10B981")
        self.card_tension = ValueCard("TENSION LUE (ADC)", "V", color="#F5A623")

        cards_layout.addWidget(self.card_vitesse)
        cards_layout.addWidget(self.card_pwm)
        cards_layout.addWidget(self.card_tension)

        top_section.addLayout(cards_layout, 1)

        # --- CONTROL PANEL (Right) ---
        control_panel = QFrame()
        control_panel.setProperty("class", "ControlPanel")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(20)

        # Sens de rotation
        dir_label = QLabel("DIRECTION DU MOTEUR")
        dir_label.setProperty("class", "CardTitle")
        control_layout.addWidget(dir_label)

        btn_dir_layout = QHBoxLayout()
        self.gauche_btn = QPushButton("← ROTATION GAUCHE")
        self.gauche_btn.setObjectName("dir_btn")
        self.gauche_btn.setCheckable(True)
        self.gauche_btn.setFixedHeight(50)

        self.droite_btn = QPushButton("ROTATION DROITE →")
        self.droite_btn.setObjectName("dir_btn")
        self.droite_btn.setCheckable(True)
        self.droite_btn.setChecked(True)
        self.droite_btn.setFixedHeight(50)

        btn_dir_layout.addWidget(self.gauche_btn)
        btn_dir_layout.addWidget(self.droite_btn)
        control_layout.addLayout(btn_dir_layout)

        control_layout.addSpacing(10)

        # Consigne de vitesse
        speed_label = QLabel("CONSIGNE DE VITESSE")
        speed_label.setProperty("class", "CardTitle")
        control_layout.addWidget(speed_label)

        self.speed_spinbox = QDoubleSpinBox()
        self.speed_spinbox.setRange(0, 4000)
        self.speed_spinbox.setValue(150)
        self.speed_spinbox.setDecimals(0)
        self.speed_spinbox.setSuffix(" RPM")
        self.speed_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.speed_spinbox)

        # Slider
        slider_layout = QHBoxLayout()
        self.vitesse_moins_btn = QPushButton("-")
        self.vitesse_moins_btn.setFixedSize(40, 40)

        self.vitesse_slider = QSlider(Qt.Orientation.Horizontal)
        self.vitesse_slider.setRange(0, 4000)
        self.vitesse_slider.setValue(150)

        self.vitesse_plus_btn = QPushButton("+")
        self.vitesse_plus_btn.setFixedSize(40, 40)

        slider_layout.addWidget(self.vitesse_moins_btn)
        slider_layout.addWidget(self.vitesse_slider)
        slider_layout.addWidget(self.vitesse_plus_btn)
        control_layout.addLayout(slider_layout)

        control_layout.addStretch()

        # Bouton Start/Stop
        self.start_btn = QPushButton("DÉMARRER LE MOTEUR")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setCheckable(True)
        control_layout.addWidget(self.start_btn)

        top_section.addWidget(control_panel, 2)
        main_layout.addLayout(top_section, 1)

        # ================= BOTTOM SECTION (GRAPHS) =================
        graph_panel = QFrame()
        graph_panel.setProperty("class", "ControlPanel")
        graph_layout = QVBoxLayout(graph_panel)
        graph_layout.setContentsMargins(5, 5, 5, 5)

        pg.setConfigOptions(antialias=True) # Lissage des courbes

        self.graph_widget = pg.PlotWidget(title="Performance en Temps Réel")
        self.graph_widget.setBackground('#1A1F29')
        self.graph_widget.setLabel('left', 'Vitesse', units='RPM')
        self.graph_widget.setLabel('bottom', 'Échantillons')
        self.graph_widget.showGrid(x=True, y=True, alpha=0.15)
        self.graph_widget.setYRange(-4500, 4500)

        # Legend
        self.graph_widget.addLegend(offset=(20, 20), pen='#2A3142', brush='#1A1F29')

        graph_layout.addWidget(self.graph_widget)
        main_layout.addWidget(graph_panel, 2)

        # Données du graphe
        self.history_size = 200
        self.plot_data_time = collections.deque(maxlen=self.history_size)
        self.plot_data_vitesse = collections.deque(maxlen=self.history_size)
        self.plot_data_consigne = collections.deque(maxlen=self.history_size)
        self.time_counter = 0

        # Styles des courbes
        pen_vitesse = pg.mkPen(color='#00D2FF', width=3)
        pen_consigne = pg.mkPen(color='#F5A623', width=2, style=Qt.PenStyle.DashLine)

        self.curve_vitesse = self.graph_widget.plot(pen=pen_vitesse, name="Vitesse Réelle")
        self.curve_consigne = self.graph_widget.plot(pen=pen_consigne, name="Consigne")

        # Remplissage sous la courbe (Fill)
        brush_vitesse = pg.mkBrush(color=(0, 210, 255, 40)) # Bleu semi-transparent
        self.curve_vitesse.setFillLevel(0)
        self.curve_vitesse.setBrush(brush_vitesse)

        # --- CONNEXIONS ---
        self.start_btn.clicked.connect(self.toggle_motor)
        self.gauche_btn.clicked.connect(self.select_direction_gauche)
        self.droite_btn.clicked.connect(self.select_direction_droite)
        self.speed_spinbox.valueChanged.connect(self.update_slider)
        self.vitesse_slider.valueChanged.connect(self.update_spinbox)
        self.vitesse_plus_btn.clicked.connect(lambda: self.speed_spinbox.setValue(self.speed_spinbox.value() + 50))
        self.vitesse_moins_btn.clicked.connect(lambda: self.speed_spinbox.setValue(max(0, self.speed_spinbox.value() - 50)))

        self.set_controls_enabled(False) # Désactivé par défaut (non connecté)


    def refresh_ports(self):
        self.port_combo.clear()
        self.port_combo.addItem("Simulation (Moteur Virtuel)")
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_combo.addItem(p.device)

    def toggle_connection(self):
        if self.connect_btn.isChecked():
            # Tente de se connecter
            port = self.port_combo.currentText()
            if port == "Aucun port trouvé" or not port:
                QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un port COM valide.")
                self.connect_btn.setChecked(False)
                return

            if port == "Simulation (Moteur Virtuel)":
                self.worker = VirtualMotorWorkerThread()
            else:
                self.worker = MotorWorkerThread(port=port)

            self.worker.data_updated.connect(self.update_ui)
            self.worker.connection_error.connect(self.on_connection_error)
            self.worker.start()

            self.connect_btn.setText("DÉCONNECTER")
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.set_controls_enabled(True)

        else:
            # Se déconnecte
            if self.worker:
                if self.worker.is_running:
                    self.start_btn.setChecked(False)
                    self.toggle_motor() # Arrête le moteur avant de couper
                self.worker.stop()
                self.worker = None

            self.connect_btn.setText("CONNECTER")
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.set_controls_enabled(False)

    def on_connection_error(self, err_msg):
        QMessageBox.critical(self, "Erreur de Connexion", err_msg)
        self.connect_btn.setChecked(False)
        self.toggle_connection() # Reset UI

    def set_controls_enabled(self, state):
        self.start_btn.setEnabled(state)
        self.gauche_btn.setEnabled(state)
        self.droite_btn.setEnabled(state)
        self.speed_spinbox.setEnabled(state)
        self.vitesse_slider.setEnabled(state)
        self.vitesse_plus_btn.setEnabled(state)
        self.vitesse_moins_btn.setEnabled(state)
        if not state:
            self.card_vitesse.set_value("0")
            self.card_pwm.set_value("0")
            self.card_tension.set_value("0.00")

    # --- GESTION DE LA DIRECTION ---
    def select_direction_gauche(self):
        self.droite_btn.setChecked(False)
        self.gauche_btn.setChecked(True)
        if self.worker: self.worker.set_direction("GAUCHE")

    def select_direction_droite(self):
        self.gauche_btn.setChecked(False)
        self.droite_btn.setChecked(True)
        if self.worker: self.worker.set_direction("DROITE")

    # --- SYNCHRONISATION UI ---
    def update_slider(self, val):
        self.vitesse_slider.blockSignals(True)
        self.vitesse_slider.setValue(int(val))
        self.vitesse_slider.blockSignals(False)
        if self.worker: self.worker.set_target_speed(val)

    def update_spinbox(self, val):
        self.speed_spinbox.blockSignals(True)
        self.speed_spinbox.setValue(val)
        self.speed_spinbox.blockSignals(False)
        if self.worker: self.worker.set_target_speed(val)

    def toggle_motor(self):
        if not self.worker: return

        if self.start_btn.isChecked():
            self.worker.set_running(True)
            self.start_btn.setText("ARRÊTER LE MOTEUR")
        else:
            self.worker.set_running(False)
            self.start_btn.setText("DÉMARRER LE MOTEUR")

    # --- LECTURE DES DONNEES STM32 ET MISE A JOUR GRAPHIQUE ---
    def update_ui(self, data):
        # Update Cards
        self.card_tension.set_value(f"{data['tension']:.2f}")
        self.card_pwm.set_value(f"{data['pwm']}")

        vitesse_actuelle = data['vitesse']
        self.card_vitesse.set_value(f"{abs(vitesse_actuelle):.0f}")

        # Update Graph Data
        self.plot_data_time.append(self.time_counter)
        self.plot_data_vitesse.append(vitesse_actuelle)

        current_consigne = self.speed_spinbox.value()
        # Consigne est negative si on tourne a gauche
        if self.gauche_btn.isChecked() and self.worker and self.worker.is_running:
            current_consigne = -current_consigne
        elif not self.worker or not self.worker.is_running:
            current_consigne = 0

        self.plot_data_consigne.append(current_consigne)
        self.time_counter += 1

        # Redraw Graph
        self.curve_vitesse.setData(list(self.plot_data_time), list(self.plot_data_vitesse))
        self.curve_consigne.setData(list(self.plot_data_time), list(self.plot_data_consigne))

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernMotorHMI()
    window.show()
    sys.exit(app.exec())
