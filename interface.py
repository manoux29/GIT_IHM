import sys
import serial
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QProgressBar, QDoubleSpinBox, QSlider, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

# --- THREAD DE COMMUNICATION SÉRIE ---
# (Identique à ton code d'origine)
class MotorWorkerThread(QThread):
    data_updated = pyqtSignal(dict)

    def __init__(self, port="COM7", baudrate=115200):
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
                            print(f"Erreur d'analyse : '{ligne}' -> {e}")
                            
        except serial.SerialException as e:
            print(f"Erreur d'ouverture du port {self.port}: {e}")
            
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
                print(f"PC -> STM32 : {cmd_str}")
            except Exception as e:
                print(f"Erreur d'envoi : {e}")

    def set_running(self, state):
        self.is_running = state
        self.send_command("START" if state else "STOP")

    def set_direction(self, direction_str):
        self.send_command(f"DIR:{direction_str}")

    def set_target_speed(self, speed):
        self.send_command(f"SPEED:{int(speed)}")


# --- STYLESHEET GLOBAL ---
QSS_STYLESHEET = """
QMainWindow { background-color: #1e2430; color: #f0f0f0; font-family: 'Segoe UI', Arial, sans-serif; }
#main_title { color: #f0f0f0; font-size: 22px; font-weight: bold; padding: 10px; }
.MeasurePanel { background-color: #2b3245; border: 1px solid #3d4661; border-radius: 10px; padding: 15px; margin: 5px; }
.MeasureLabel { color: #8c98ac; font-size: 11px; font-weight: bold; text-transform: uppercase; }
.MeasureValue { color: #4cdfff; font-size: 28px; font-weight: bold; padding-top: 5px; }
QProgressBar { background-color: #1e2430; border: none; border-radius: 5px; text-align: center; height: 10px; }
QProgressBar::chunk { background-color: #4cdfff; border-radius: 5px; }
.CentralPanel { background-color: #2b3245; border: 1px solid #3d4661; border-radius: 10px; padding: 15px; margin: 5px; }

/* Boutons classiques */
QPushButton { background-color: #3d4661; color: white; border: none; border-radius: 5px; padding: 10px 15px; font-weight: bold; font-size: 14px;}
QPushButton:hover { background-color: #4d597c; }

/* Bouton Démarrer */
#demarrer_btn { background-color: #1ccdfc; color: #1e2430; font-size: 16px; padding: 15px;}
#demarrer_btn:hover { background-color: #66e7ff; }

/* Boutons de Direction (Toggle) */
#dir_btn { background-color: #1e2430; color: #8c98ac; border: 2px solid #3d4661; }
#dir_btn:hover { background-color: #2b3245; }
#dir_btn:checked { background-color: #2b3245; color: #4cdfff; border: 2px solid #4cdfff; }

QDoubleSpinBox { background-color: #1e2430; color: #f0f0f0; border: 1px solid #3d4661; border-radius: 5px; padding: 10px; font-size: 18px; font-weight: bold; }
QSlider::groove:horizontal { border: none; height: 8px; background: #1e2430; border-radius: 4px; }
QSlider::handle:horizontal { background: #4cdfff; border: none; width: 20px; height: 20px; margin: -6px 0; border-radius: 10px; }
"""

# --- WIDGET DE MESURE ---
class MeasurementPanel(QFrame):
    def __init__(self, title, unit, is_large=False):
        super().__init__()
        self.setProperty("class", "MeasurePanel")
        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "MeasureLabel")
        layout.addWidget(self.title_label)

        value_layout = QHBoxLayout()
        self.value_label = QLabel("0")
        self.value_label.setProperty("class", "MeasureValue")
        if is_large: self.value_label.setStyleSheet("font-size: 36px;")
             
        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet("color: #8c98ac; font-size: 14px; font-weight: bold; padding-bottom: 5px;")
        
        value_layout.addWidget(self.value_label, alignment=Qt.AlignmentFlag.AlignBottom)
        value_layout.addWidget(self.unit_label, alignment=Qt.AlignmentFlag.AlignBottom)
        value_layout.addStretch()
        layout.addLayout(value_layout)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

    def set_value(self, value_str, progress_perc):
        self.value_label.setText(value_str)
        self.progress_bar.setValue(int(progress_perc))


# --- FENÊTRE PRINCIPALE ---
class ModernMotorHMI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IHM Moteur Complète")
        self.resize(1100, 650)
        self.setStyleSheet(QSS_STYLESHEET)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("CONTRÔLE ET DIAGNOSTIC MOTEUR")
        title_label.setObjectName("main_title")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # --- COLONNE 1 : LECTURE DES DONNÉES ---
        col1_layout = QVBoxLayout()
        self.panel_adc = MeasurementPanel("Valeur ADC Lues", " / 4095")
        self.panel_adc.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f5a623; }")
        col1_layout.addWidget(self.panel_adc)
        
        self.panel_tension = MeasurementPanel("Tension", "V")
        col1_layout.addWidget(self.panel_tension)
        
        self.panel_pwm = MeasurementPanel("PWM STM32", " / 2099")
        self.panel_pwm.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #7ed321; }")
        col1_layout.addWidget(self.panel_pwm)
        
        self.panel_vitesse = MeasurementPanel("Vitesse Réelle", "RPM", is_large=True)
        col1_layout.addWidget(self.panel_vitesse)
        
        content_layout.addLayout(col1_layout, 1)

        # --- COLONNE 2 : VISUALISATION (IMAGE) ---
        motor_panel = QFrame()
        motor_panel.setProperty("class", "CentralPanel")
        motor_layout = QVBoxLayout(motor_panel)
        motor_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Intégration de l'image
        self.motor_image = QLabel()
        # Assure-toi que "motor_icon.png" existe dans le même dossier
        pixmap = QPixmap("motor_icon.png") 
        if not pixmap.isNull():
            # Redimensionne l'image pour qu'elle s'intègre bien sans être déformée
            self.motor_image.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.motor_image.setText("[ Image motor_icon.png introuvable ]")
            self.motor_image.setStyleSheet("color: #8c98ac; font-size: 14px; font-style: italic;")
            
        self.motor_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(self.motor_image)

        # Indicateurs de flèches (feedback réel du moteur)
        dir_layout = QHBoxLayout()
        self.dir_left_indic = QLabel("←")
        self.dir_right_indic = QLabel("→")
        self.dir_left_indic.setStyleSheet("color: #3d4661; font-size: 60px; font-weight: bold;")
        self.dir_right_indic.setStyleSheet("color: #3d4661; font-size: 60px; font-weight: bold;")
        dir_layout.addStretch()
        dir_layout.addWidget(self.dir_left_indic)
        dir_layout.addSpacing(40)
        dir_layout.addWidget(self.dir_right_indic)
        dir_layout.addStretch()
        motor_layout.addLayout(dir_layout)
        
        content_layout.addWidget(motor_panel, 1)

        # --- COLONNE 3 : CONTRÔLE ---
        control_panel = QFrame()
        control_panel.setProperty("class", "CentralPanel")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(20) # Aère les éléments

        # 1. Sélection de la direction
        dir_label = QLabel("SENS DE ROTATION SOUHAITÉ")
        dir_label.setStyleSheet("color: #8c98ac; font-size: 12px; font-weight: bold;")
        control_layout.addWidget(dir_label)

        btn_dir_layout = QHBoxLayout()
        self.gauche_btn = QPushButton("← GAUCHE")
        self.gauche_btn.setObjectName("dir_btn")
        self.gauche_btn.setCheckable(True) # Rend le bouton "activable"
        
        self.droite_btn = QPushButton("DROITE →")
        self.droite_btn.setObjectName("dir_btn")
        self.droite_btn.setCheckable(True)
        self.droite_btn.setChecked(True) # Par défaut, on tourne à droite
        
        btn_dir_layout.addWidget(self.gauche_btn)
        btn_dir_layout.addWidget(self.droite_btn)
        control_layout.addLayout(btn_dir_layout)

        # 2. Consigne de vitesse
        control_layout.addSpacing(10)
        speed_label = QLabel("CONSIGNE VITESSE (PC)")
        speed_label.setStyleSheet("color: #8c98ac; font-size: 12px; font-weight: bold;")
        control_layout.addWidget(speed_label)

        self.speed_spinbox = QDoubleSpinBox()
        self.speed_spinbox.setRange(0, 17)
        self.speed_spinbox.setValue(8)
        self.speed_spinbox.setSuffix(" RPM")
        self.speed_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.speed_spinbox)

        # Slider avec boutons +/-
        slider_layout = QHBoxLayout()
        self.vitesse_moins_btn = QPushButton("-")
        self.vitesse_moins_btn.setFixedWidth(40)
        
        self.vitesse_slider = QSlider(Qt.Orientation.Horizontal)
        self.vitesse_slider.setRange(0, 17)
        self.vitesse_slider.setValue(8)
        
        self.vitesse_plus_btn = QPushButton("+")
        self.vitesse_plus_btn.setFixedWidth(40)
        
        slider_layout.addWidget(self.vitesse_moins_btn)
        slider_layout.addWidget(self.vitesse_slider)
        slider_layout.addWidget(self.vitesse_plus_btn)
        control_layout.addLayout(slider_layout)

        control_layout.addStretch() # Pousse le bouton démarrer vers le bas

        # 3. Bouton Démarrer/Arrêter
        self.demarrer_btn = QPushButton("DÉMARRER LE MOTEUR")
        self.demarrer_btn.setObjectName("demarrer_btn")
        control_layout.addWidget(self.demarrer_btn)

        content_layout.addWidget(control_panel, 1)

        # --- INITIALISATION ET CONNEXIONS ---
        self.worker = MotorWorkerThread(port="COM7")
        self.worker.data_updated.connect(self.update_ui)
        self.worker.start()

        self.demarrer_btn.clicked.connect(self.toggle_motor)
        
        # Logique des boutons de direction
        self.gauche_btn.clicked.connect(self.select_direction_gauche)
        self.droite_btn.clicked.connect(self.select_direction_droite)
        
        # Synchronisation slider/spinbox
        self.speed_spinbox.valueChanged.connect(self.update_slider)
        self.vitesse_slider.valueChanged.connect(self.update_spinbox)
        self.vitesse_plus_btn.clicked.connect(lambda: self.speed_spinbox.setValue(self.speed_spinbox.value() + 1))
        self.vitesse_moins_btn.clicked.connect(lambda: self.speed_spinbox.setValue(max(0, self.speed_spinbox.value() - 1)))

    # --- GESTION DE LA DIRECTION ---
    def select_direction_gauche(self):
        self.droite_btn.setChecked(False) # Désactive l'autre bouton
        self.gauche_btn.setChecked(True)  # Force celui-ci à rester actif
        self.worker.set_direction("GAUCHE")

    def select_direction_droite(self):
        self.gauche_btn.setChecked(False)
        self.droite_btn.setChecked(True)
        self.worker.set_direction("DROITE")

    # --- SYNCHRONISATION UI ---
    def update_slider(self, val):
        self.vitesse_slider.blockSignals(True)
        self.vitesse_slider.setValue(int(val))
        self.vitesse_slider.blockSignals(False)
        self.worker.set_target_speed(val)

    def update_spinbox(self, val):
        self.speed_spinbox.blockSignals(True)
        self.speed_spinbox.setValue(val)
        self.speed_spinbox.blockSignals(False)
        self.worker.set_target_speed(val)

    def toggle_motor(self):
        if self.worker.is_running:
            self.worker.set_running(False)
            self.demarrer_btn.setText("DÉMARRER LE MOTEUR")
            self.demarrer_btn.setStyleSheet("") 
        else:
            self.worker.set_running(True)
            self.demarrer_btn.setText("ARRÊTER LE MOTEUR")
            self.demarrer_btn.setStyleSheet("background-color: #ff4c4c; color: white;") 

    # --- LECTURE DES DONNEES STM32 ---
    def update_ui(self, data):
        self.panel_adc.set_value(f"{data['adc']}", (data['adc'] / 4095.0) * 100)
        self.panel_tension.set_value(f"{data['tension']:.2f}", (data['tension'] / 3.3) * 100)
        self.panel_pwm.set_value(f"{data['pwm']}", (data['pwm'] / 2099.0) * 100)
        
        vitesse_abs = abs(data['vitesse'])
        self.panel_vitesse.set_value(f"{vitesse_abs:.0f}", min((vitesse_abs / 17.0) * 100, 100))
        
        # Flèches centrales basées sur la VRAIE vitesse (feedback)
        if data['vitesse'] < 0:
            self.dir_left_indic.setStyleSheet("color: #4cdfff; font-size: 60px; font-weight: bold;")
            self.dir_right_indic.setStyleSheet("color: #3d4661; font-size: 60px; font-weight: bold;")
        elif data['vitesse'] > 0:
            self.dir_right_indic.setStyleSheet("color: #4cdfff; font-size: 60px; font-weight: bold;")
            self.dir_left_indic.setStyleSheet("color: #3d4661; font-size: 60px; font-weight: bold;")
        else: # À l'arrêt
            self.dir_left_indic.setStyleSheet("color: #3d4661; font-size: 60px; font-weight: bold;")
            self.dir_right_indic.setStyleSheet("color: #3d4661; font-size: 60px; font-weight: bold;")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernMotorHMI()
    window.show()
    sys.exit(app.exec())