import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QPushButton, QLabel)
from mahjong.constants import EAST, SOUTH, WEST, NORTH
from logic import MahjongAnalyzer
from vision import TableEye

class AlphaJongCompanion(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.analyzer = MahjongAnalyzer()
        self.eye = TableEye()  # 👁️ Наше зоркое всевидящее око
        
        # 💡 Только твоя рука и сбросы — ничего лишнего!
        self.my_hand = []
        self.my_discards = []
        self.dora_indicators = []
        
        self.active_target = 'hand'  # 'hand' или 'dora'
        self.action_history = []
        
        self.tile_display_names = {
            "1z": "E", "2z": "S", "3z": "W", "4z": "N",
            "5z": "Бел", "6z": "Зел", "7z": "Крас",
            "0m": "🔴5m", "0p": "🔴5p", "0s": "🔴5s"
        }
        
        self.winds_chars = ["E", "S", "W", "N"]
        self.winds_constants = [EAST, SOUTH, WEST, NORTH]
        self.round_wind_idx = 0
        self.my_wind_idx = 0
        
        self.drag_position = None
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(580, 520)
        self.main_widget = QWidget(self)
        self.main_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 25, 240);
                color: #E0E0E0;
                border-radius: 12px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QPushButton {
                background-color: rgba(60, 60, 80, 200);
                border: 1px solid #555;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover { background-color: rgba(90, 90, 120, 255); }
            QPushButton:pressed { background-color: rgba(180, 60, 80, 255); }
            QLabel { background: transparent; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self.main_widget)
        
        # === ВЕРХНЯЯ ПАНЕЛЬ: ВЕТРА, СКАН И ОЧИСТКА ===
        top_layout = QHBoxLayout()
        self.round_wind_btn = QPushButton(f"Раунд: {self.winds_chars[self.round_wind_idx]}")
        self.round_wind_btn.clicked.connect(self.cycle_round_wind)
        
        self.my_wind_btn = QPushButton(f"Мой Ветер: {self.winds_chars[self.my_wind_idx]}")
        self.my_wind_btn.clicked.connect(self.cycle_my_wind)
        
        self.scan_btn = QPushButton("👁️ Скан стола")
        self.scan_btn.setStyleSheet("background-color: rgba(40, 140, 100, 220); font-weight: bold; color: white;")
        self.scan_btn.clicked.connect(self.auto_scan_table)
        
        self.clear_btn = QPushButton("Очистить стол ❌")
        self.clear_btn.setStyleSheet("background-color: rgba(180, 50, 50, 200);")
        self.clear_btn.clicked.connect(self.clear_table)
        
        self.exit_btn = QPushButton("❌")
        self.exit_btn.setFixedSize(28, 28)
        self.exit_btn.setStyleSheet("background-color: transparent; border: none; font-size: 16px;")
        self.exit_btn.clicked.connect(self.force_exit)  # 💡 Подключили мгновенное убийство процесса
        
        top_layout.addWidget(self.round_wind_btn)
        top_layout.addWidget(self.my_wind_btn)
        top_layout.addWidget(self.scan_btn)
        top_layout.addStretch()
        top_layout.addWidget(self.clear_btn)
        top_layout.addWidget(self.exit_btn)
        layout.addLayout(top_layout)
        
        # === ПАНЕЛЬ ФОКУСА ВВОДА И ОТМЕНЫ ===
        focus_layout = QHBoxLayout()
        focus_layout.addWidget(QLabel("Ввод палитры:"))
        
        self.btn_focus_hand = QPushButton("✋ Моя рука")
        self.btn_focus_hand.setCheckable(True)
        self.btn_focus_hand.setChecked(True)
        self.btn_focus_hand.clicked.connect(lambda: self.set_focus('hand'))
        
        self.btn_focus_dora = QPushButton("🐉 Индикаторы Доры")
        self.btn_focus_dora.setCheckable(True)
        self.btn_focus_dora.setStyleSheet("background-color: rgba(160, 140, 40, 180);")
        self.btn_focus_dora.clicked.connect(lambda: self.set_focus('dora'))
        
        self.undo_btn = QPushButton("↩ Отменить")
        self.undo_btn.setFixedSize(100, 28)
        self.undo_btn.setStyleSheet("background-color: rgba(100, 60, 120, 200);")
        self.undo_btn.clicked.connect(self.undo_action)
        
        focus_layout.addWidget(self.btn_focus_hand)
        focus_layout.addWidget(self.btn_focus_dora)
        focus_layout.addStretch()
        focus_layout.addWidget(self.undo_btn)
        layout.addLayout(focus_layout)
        
        # === ИНДИКАТОРЫ ДОРЫ ===
        self.dora_label = QLabel("✨ Индикаторы Доры: [Пусто]")
        self.dora_label.setStyleSheet("color: #FFD700; font-size: 13px; margin-top: 2px;")
        layout.addWidget(self.dora_label)

        # === ЛОГ СТАТУСА ===
        self.log_label = QLabel("📝 Лог: Готов к расчетам. Жми [👁️ Скан стола]!")
        self.log_label.setStyleSheet("color: #FF99BB; font-size: 13px;")
        layout.addWidget(self.log_label)
        
        # === ПАЛИТРА КОСТЕЙ С АКА-ДОРАМИ ===
        layout.addWidget(QLabel("Палитра костей (Клик = Добавить в фокус):"))
        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        
        suits = [
            ("Ман (m)", ["1m","2m","3m","4m","5m","0m","6m","7m","8m","9m"]),
            ("Пин (p)", ["1p","2p","3p","4p","5p","0p","6p","7p","8p","9p"]),
            ("Соу (s)", ["1s","2s","3s","4s","5s","0s","6s","7s","8s","9s"]),
            ("Ветра/Драк (z)", ["1z","2z","3z","4z","5z","6z","7z"])
        ]
        
        row = 0
        for suit_name, tiles in suits:
            grid_layout.addWidget(QLabel(suit_name), row, 0)
            for col, tile_str in enumerate(tiles):
                display_text = self.tile_display_names.get(tile_str, tile_str)
                btn = QPushButton(display_text)
                btn.setFixedSize(38, 38)
                if "0" in tile_str:
                    btn.setStyleSheet("background-color: rgba(180, 50, 50, 220); color: white; border: 1px solid #FF8888;")
                btn.clicked.connect(lambda checked, t=tile_str: self.handle_palette_click(t))
                grid_layout.addWidget(btn, row, col+1)
            row += 1
        layout.addLayout(grid_layout)
        
        # === МОЯ РУКА ===
        self.hand_label = QLabel("Моя рука (0/14) [Клик по кости = Сбросить]:")
        layout.addWidget(self.hand_label)
        
        self.hand_layout = QHBoxLayout()
        self.hand_layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(self.hand_layout)
        
        # === СОВЕТ КАЛЬКУЛЯТОРА ===
        self.advice_label = QLabel("🔮 Совет: Нажми [👁️ Скан стола] для расчета сброса...")
        self.advice_label.setStyleSheet("color: #FF99BB; font-size: 13px; padding-top: 5px;")
        self.advice_label.setWordWrap(True)
        layout.addWidget(self.advice_label)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.main_widget)
        self.setLayout(main_layout)
        self.move(100, 100)

    # ==========================
    #   МАГИЯ КОМПЬЮТЕРНОГО ЗРЕНИЯ
    # ==========================
    def _map_scanned_tile(self, name):
        """Переводит имена шаблонов 5am/5ap/5as в системные коды 0m/0p/0s"""
        if name == "5am": return "0m"
        if name == "5ap": return "0p"
        if name == "5as": return "0s"
        return name

    def auto_scan_table(self):
        self.log_label.setText("👁️ Сканирую экран... Не двигай мышь!")
        QApplication.processEvents()
        
        scanned_hand_raw = self.eye.scan_my_hand()
        scanned_hand = [self._map_scanned_tile(t) for t in scanned_hand_raw]
        
        scanned_dora_raw = self.eye.scan_dora_box()
        scanned_dora = [self._map_scanned_tile(t) for t in scanned_dora_raw]
        
        if scanned_hand:
            self.my_hand = scanned_hand[:14]  # Максимум 14 тайлов
            display_str = " ".join([self.tile_display_names.get(t, t) for t in self.my_hand])
            self.log_label.setText(f"👁️ Распознана рука ({len(self.my_hand)}): {display_str}")
        else:
            self.log_label.setText("⚠️ Рука не распознана! Проверь шаблоны в папке templates.")
            
        if scanned_dora:
            self.dora_indicators = scanned_dora
            
        self.update_ui_state()

    # ==========================
    #      УПРАВЛЕНИЕ ОКНОМ
    # ==========================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()

    def force_exit(self):
        """💡 Лисья гильотина: мгновенное убийство процесса по кнопке ❌"""
        self.close()
        os._exit(0)

    def closeEvent(self, event):
        """💡 Срабатывает при закрытии окна через Alt+F4 или панель задач"""
        event.accept()
        os._exit(0)

    def cycle_round_wind(self):
        self.round_wind_idx = (self.round_wind_idx + 1) % 4
        self.round_wind_btn.setText(f"Раунд: {self.winds_chars[self.round_wind_idx]}")
        self.update_ui_state()

    def cycle_my_wind(self):
        self.my_wind_idx = (self.my_wind_idx + 1) % 4
        self.my_wind_btn.setText(f"Мой Ветер: {self.winds_chars[self.my_wind_idx]}")
        self.update_ui_state()

    def set_focus(self, target):
        self.active_target = target
        self.btn_focus_hand.setChecked(target == 'hand')
        self.btn_focus_dora.setChecked(target == 'dora')
        label = "Моя рука" if target == 'hand' else "Индикаторы Доры"
        self.log_label.setText(f"📝 Фокус ввода переключен на: [{label}]")

    # ==========================
    #        РУЧНОЙ ВВОД
    # ==========================
    def handle_palette_click(self, tile_str):
        display_tile = self.tile_display_names.get(tile_str, tile_str)
        
        if self.active_target == 'dora':
            self.dora_indicators.append(tile_str)
            self.action_history.append(('add_dora', tile_str))
            self.log_label.setText(f"✨ Добавлен Индикатор Доры: {display_tile}")
        else:
            if len(self.my_hand) < 14:
                self.my_hand.append(tile_str)
                self.action_history.append(('add_hand', tile_str))
                self.log_label.setText(f"📝 В руку добавлено: {display_tile}")
            else:
                self.log_label.setText("⚠️ В руке уже 14 костей!")
                
        self.update_ui_state()

    def discard_my_tile(self, index):
        if 0 <= index < len(self.my_hand):
            tile = self.my_hand.pop(index)
            self.my_discards.append(tile)
            self.action_history.append(('discard', index, tile))
            display_tile = self.tile_display_names.get(tile, tile)
            self.log_label.setText(f"🗑️ Сброшено из руки: {display_tile}")
            self.update_ui_state()

    def undo_action(self):
        if not self.action_history:
            self.log_label.setText("⚠️ Нечего отменять!")
            return
        
        last_action = self.action_history.pop()
        action_type = last_action[0]
        
        if action_type == 'add_hand':
            if self.my_hand:
                self.my_hand.pop()
                self.log_label.setText("↩ Отменено: удален тайл из руки")
        elif action_type == 'add_dora':
            if self.dora_indicators:
                self.dora_indicators.pop()
                self.log_label.setText("↩ Отменено: удален Индикатор Доры")
        elif action_type == 'discard':
            _, idx, tile = last_action
            if self.my_discards:
                self.my_discards.pop()
            self.my_hand.insert(idx, tile)
            self.log_label.setText("↩ Отменено: тайл возвращен в руку")
            
        self.update_ui_state()

    def clear_table(self):
        self.my_hand.clear()
        self.my_discards.clear()
        self.dora_indicators.clear()
        self.action_history.clear()
        self.update_ui_state()
        self.log_label.setText("🔮 Стол полностью очищен. Новая раздача!")

    # ==========================
    #     ОТРИСОВКА И РАСЧЕТ
    # ==========================
    def update_ui_state(self):
        self.hand_label.setText(f"Моя рука ({len(self.my_hand)}/14) [Клик по кости = Сбросить]:")
        
        for i in reversed(range(self.hand_layout.count())):
            widget = self.hand_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
                
        for idx, tile in enumerate(self.my_hand):
            display_text = self.tile_display_names.get(tile, tile)
            btn = QPushButton(display_text)
            btn.setFixedSize(38, 52)
            if "0" in tile:
                btn.setStyleSheet("background-color: rgba(180, 50, 50, 220); color: white; border: 1px solid #FF8888;")
            else:
                btn.setStyleSheet("background-color: rgba(90, 150, 90, 200); color: white;")
            btn.clicked.connect(lambda checked, i=idx: self.discard_my_tile(i))
            self.hand_layout.addWidget(btn)
            
        dora_str = ", ".join([self.tile_display_names.get(d, d) for d in self.dora_indicators]) if self.dora_indicators else "[Пусто]"
        self.dora_label.setText(f"✨ Индикаторы Доры: {dora_str}")
            
        if len(self.my_hand) in [14, 11, 8, 5]:
            r_wind = self.winds_constants[self.round_wind_idx]
            p_wind = self.winds_constants[self.my_wind_idx]
            
            advice = self.analyzer.analyze_hand(
                self.my_hand, 
                [],  # all_table_discards
                self.my_discards, 
                [],  # melds
                r_wind,
                p_wind,
                self.dora_indicators
            )
            self.advice_label.setText(advice)
        else:
            self.advice_label.setText("🔮 Жду нужное количество костей для расчета (14, 11, 8, 5)...")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AlphaJongCompanion()
    window.show()
    sys.exit(app.exec_())