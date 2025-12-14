import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QMenu,
                            QDialog, QVBoxLayout, QHBoxLayout, QSlider, QCheckBox,
                            QPushButton, QGraphicsDropShadowEffect, QWidget,
                            QListWidget, QLineEdit, QSpinBox)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPixmap, QAction, QTransform, QColor


SETTINGS_FILE = "settings.json"




class SpeechBubble(QWidget):
   def __init__(self):
       super().__init__()
       self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
       self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


       layout = QVBoxLayout()
       layout.setContentsMargins(0, 0, 0, 0)
       self.setLayout(layout)


       self.label = QLabel()
       self.label.setWordWrap(True)
       self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
       self.label.setStyleSheet("""
           QLabel {
               background-color: white;
               color: black;
               border: 2px solid #444;
               border-radius: 10px;
               padding: 10px;
               font-family: Arial;
               font-size: 13px;
               font-weight: bold;
           }
       """)


       self.label.setMinimumWidth(80)
       self.label.setMaximumWidth(250)


       shadow = QGraphicsDropShadowEffect()
       shadow.setBlurRadius(15)
       shadow.setColor(QColor(0, 0, 0, 80))
       shadow.setOffset(4, 4)
       self.label.setGraphicsEffect(shadow)


       layout.addWidget(self.label)


   def update_text(self, text):
       self.label.setText(text)
       self.label.adjustSize()
       self.adjustSize()




class SettingsDialog(QDialog):
   def __init__(self, companion_window):
       super().__init__(parent=None)
       self.setWindowTitle("Settings")
       self.companion = companion_window
       self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
       self.setFixedWidth(350)


       layout = QVBoxLayout()


       layout.addWidget(QLabel("<b>Appearance</b>"))


       layout.addWidget(QLabel("Size (%)"))
       self.slider = QSlider(Qt.Orientation.Horizontal)
       self.slider.setRange(20, 200)
       self.slider.setValue(int(self.companion.scale_factor * 100))
       self.slider.valueChanged.connect(self.update_scale)
       layout.addWidget(self.slider)


       self.flip_check = QCheckBox("Flip Horizontally")
       self.flip_check.setChecked(self.companion.is_flipped)
       self.flip_check.toggled.connect(self.update_flip)
       layout.addWidget(self.flip_check)


       layout.addSpacing(10)
       layout.addWidget(QLabel("<b>Reminders Manager</b>"))


       self.phrase_list_widget = QListWidget()
       self.refresh_list()
       layout.addWidget(self.phrase_list_widget)


       layout.addWidget(QLabel("Add New Reminder:"))
       input_layout = QHBoxLayout()


       self.phrase_input = QLineEdit()
       self.phrase_input.setPlaceholderText("Message...")
       input_layout.addWidget(self.phrase_input)


       self.time_input = QSpinBox()
       self.time_input.setRange(5, 3600)
       self.time_input.setValue(60)
       self.time_input.setSuffix(" sec")
       input_layout.addWidget(self.time_input)


       add_btn = QPushButton("Add")
       add_btn.clicked.connect(self.add_reminder)
       input_layout.addWidget(add_btn)


       layout.addLayout(input_layout)


       remove_btn = QPushButton("Remove Selected")
       remove_btn.clicked.connect(self.remove_reminder)
       layout.addWidget(remove_btn)


       layout.addSpacing(10)
       self.save_btn = QPushButton("Save & Close")
       self.save_btn.clicked.connect(self.save_and_close)
       self.save_btn.setStyleSheet("background-color: #DDDDDD; padding: 8px; font-weight: bold;")
       layout.addWidget(self.save_btn)


       self.setLayout(layout)


   def refresh_list(self):
       self.phrase_list_widget.clear()
       for item in self.companion.reminders:
           display_text = f"{item['text']} (every {item['interval']}s)"
           self.phrase_list_widget.addItem(display_text)


   def update_scale(self, value):
       self.companion.set_scale(value / 100.0)


   def update_flip(self, checked):
       self.companion.set_flip(checked)


   def add_reminder(self):
       text = self.phrase_input.text().strip()
       seconds = self.time_input.value()


       if text:
           new_reminder = {
               "text": text,
               "interval": seconds,
               "counter": 0
           }
           self.companion.reminders.append(new_reminder)
           self.phrase_input.clear()
           self.refresh_list()


   def remove_reminder(self):
       current_row = self.phrase_list_widget.currentRow()
       if current_row >= 0:
           del self.companion.reminders[current_row]
           self.refresh_list()


   def save_and_close(self):
       self.companion.save_state()
       self.accept()




class DesktopCompanion(QMainWindow):
   def __init__(self):
       super().__init__()


       self.setWindowFlags(
           Qt.WindowType.FramelessWindowHint |
           Qt.WindowType.WindowStaysOnTopHint |
           Qt.WindowType.Tool
       )
       self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


       self.dragging = False
       self.offset = QPoint()
       self.current_sprite_state = "normal"
       self.busy_states = ["speaking", "yawn_1", "yawn_2", "bob_l", "bob_r"]
       self.scale_factor = 1.0
       self.is_flipped = False


       self.reminders = [
           {"text": "Hydrate!", "interval": 1800, "counter": 0},
           {"text": "Posture Check", "interval": 600, "counter": 0},
           {"text": "You are doing great today!", "interval": 3600, "counter": 0}
       ]


       self.assets = {}
       self.load_assets()

       self.label = QLabel(self)
       self.bubble = SpeechBubble()

       self.load_state()

       self.idle_timer = QTimer(self)
       self.idle_timer.setInterval(10000)
       self.idle_timer.timeout.connect(self.animate_blink)
       self.idle_timer.start()


       self.yawn_timer = QTimer(self)
       self.yawn_timer.setInterval(90000)
       self.yawn_timer.timeout.connect(self.animate_yawn)
       self.yawn_timer.start()

       self.headbob_timer = QTimer(self)
       self.headbob_timer.setInterval(20000)
       self.headbob_timer.timeout.connect(self.animate_headbob)
       self.headbob_timer.start()

       self.tick_timer = QTimer(self)
       self.tick_timer.setInterval(1000)
       self.tick_timer.timeout.connect(self.process_reminders)
       self.tick_timer.start()


   def load_assets(self):
       filenames = {
           "normal": "character_sprite.png",
           "half": "character_sprite_half_closed_eyes.png",
           "closed": "character_sprite_closed_eyes.png",
           "speaking": "character_sprite_speaking.png",
           "yawn_1": "character_sprite_yawn_1.png",
           "yawn_2": "character_sprite_yawn_2.png",
           "bob_l": "character_sprite_bob_l.png",
           "bob_r": "character_sprite_bob_r.png"
       }
       for state, filename in filenames.items():
           if os.path.exists(filename):
               self.assets[state] = QPixmap(filename)
           else:
               if state == "speaking" and "normal" in self.assets:
                   self.assets["speaking"] = self.assets["normal"]
               if state.startswith("yawn") and "closed" in self.assets:
                   self.assets[state] = self.assets["closed"]
               # Fallback for bobbing (use normal if missing)
               if state.startswith("bob") and "normal" in self.assets:
                   self.assets[state] = self.assets["normal"]


   def save_state(self):
       data_to_save = []
       for r in self.reminders:
           data_to_save.append({
               "text": r["text"],
               "interval": r["interval"]
           })


       state = {
           "x": self.pos().x(),
           "y": self.pos().y(),
           "scale": self.scale_factor,
           "flipped": self.is_flipped,
           "reminders": data_to_save
       }
       try:
           with open(SETTINGS_FILE, "w") as f:
               json.dump(state, f, indent=4)
           print("State saved.")
       except Exception as e:
           print(f"Error saving: {e}")


   def load_state(self):
       if os.path.exists(SETTINGS_FILE):
           try:
               with open(SETTINGS_FILE, "r") as f:
                   state = json.load(f)
                   self.scale_factor = state.get("scale", 1.0)
                   self.is_flipped = state.get("flipped", False)
                   self.move(state.get("x", 100), state.get("y", 100))


                   saved_reminders = state.get("reminders", [])
                   if saved_reminders:
                       self.reminders = []
                       for item in saved_reminders:
                           self.reminders.append({
                               "text": item["text"],
                               "interval": item["interval"],
                               "counter": 0
                           })


           except Exception as e:
               print(f"Error loading settings: {e}")


       self.update_appearance("normal")


   def set_scale(self, scale):
       self.scale_factor = scale
       self.update_appearance(self.current_sprite_state)
       if self.bubble.isVisible():
           self.update_bubble_position()


   def set_flip(self, flipped):
       self.is_flipped = flipped
       self.update_appearance(self.current_sprite_state)
       if self.bubble.isVisible():
           self.update_bubble_position()


   def update_appearance(self, state):
       if state not in self.assets: return
       self.current_sprite_state = state
       pixmap = self.assets[state]


       if self.scale_factor != 1.0:
           w = int(pixmap.width() * self.scale_factor)
           h = int(pixmap.height() * self.scale_factor)
           pixmap = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


       if self.is_flipped:
           pixmap = pixmap.transformed(QTransform().scale(-1, 1))


       self.label.setPixmap(pixmap)
       self.label.resize(pixmap.size())
       self.resize(pixmap.size())
       self.setMask(pixmap.mask())


   def process_reminders(self):
       settings_open = hasattr(self, 'settings_window') and self.settings_window.isVisible()
       if not settings_open:
           self.raise_()


       if self.bubble.isVisible():
           return


       for item in self.reminders:
           item["counter"] += 1
           if item["counter"] >= item["interval"]:
               self.trigger_message(item["text"])
               item["counter"] = 0
               break


   def trigger_message(self, text):
       self.bubble.update_text(text)
       self.update_appearance("speaking")
       self.update_bubble_position()
       self.bubble.show()
       self.bubble.raise_()
       QTimer.singleShot(4000, self.finish_speaking)


   def finish_speaking(self):
       self.bubble.hide()
       self.update_appearance("normal")


   def update_bubble_position(self):
       margin = -45
       sprite_geo = self.geometry()
       bubble_geo = self.bubble.geometry()
       y_pos = sprite_geo.top()


       if self.is_flipped:
           x_pos = sprite_geo.left() - bubble_geo.width() - margin
       else:
           x_pos = sprite_geo.right() + margin


       self.bubble.move(x_pos, y_pos)


   # --- Animations ---
   def animate_blink(self):
       if self.current_sprite_state in self.busy_states: return


       self.update_appearance("half")
       QTimer.singleShot(100, lambda: self.update_appearance("closed"))
       QTimer.singleShot(200, lambda: self.update_appearance("half"))
       QTimer.singleShot(300, lambda: self.update_appearance("normal"))


   def animate_yawn(self):
       if self.current_sprite_state in self.busy_states: return


       if "yawn_1" in self.assets and "yawn_2" in self.assets:
           self.update_appearance("yawn_1")
           QTimer.singleShot(600, lambda: self.update_appearance("yawn_2"))
           QTimer.singleShot(2000, lambda: self.update_appearance("yawn_1"))
           QTimer.singleShot(2600, lambda: self.update_appearance("normal"))


   # --- FIXED HEADBOB ANIMATION ---
   def animate_headbob(self):
       if self.current_sprite_state in self.busy_states: return


       # Sequence: bob_l -> normal -> bob_r -> normal
       if "bob_l" in self.assets and "bob_r" in self.assets:
           self.update_appearance("bob_l")
           QTimer.singleShot(1000, lambda: self.update_appearance("normal"))
           QTimer.singleShot(2000, lambda: self.update_appearance("bob_r"))
           QTimer.singleShot(3000, lambda: self.update_appearance("normal"))


   # --- Interaction ---
   def mousePressEvent(self, event):
       if event.button() == Qt.MouseButton.LeftButton:
           self.dragging = True
           self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
       elif event.button() == Qt.MouseButton.RightButton:
           self.show_context_menu(event.globalPosition().toPoint())


   def mouseMoveEvent(self, event):
       if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
           self.move(event.globalPosition().toPoint() - self.offset)
           if self.bubble.isVisible():
               self.update_bubble_position()


   def mouseReleaseEvent(self, event):
       if event.button() == Qt.MouseButton.LeftButton:
           self.dragging = False


   def show_context_menu(self, pos):
       menu = QMenu(self)
       menu.setStyleSheet(
           "QMenu { background-color: #FFF; color: black; border: 1px solid gray; } QMenu::item:selected { background-color: #DDD; }")


       settings_action = QAction("Settings", self)
       settings_action.triggered.connect(self.open_settings)
       menu.addAction(settings_action)


       exit_action = QAction("Exit Companion", self)
       exit_action.triggered.connect(QApplication.instance().quit)
       menu.addAction(exit_action)

       menu.exec(pos)


   def open_settings(self):
       if hasattr(self, 'settings_window') and self.settings_window.isVisible():
           self.settings_window.raise_()
           self.settings_window.activateWindow()
           return
       self.settings_window = SettingsDialog(self)
       self.settings_window.show()


if __name__ == "__main__":
   app = QApplication(sys.argv)
   app.setQuitOnLastWindowClosed(False)
   companion = DesktopCompanion()
   companion.show()
   sys.exit(app.exec())