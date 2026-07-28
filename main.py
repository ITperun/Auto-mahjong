import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QPushButton, QLabel, QButtonGroup)

from logic import MahjongAnalyzer

class AlphaJongCompanion(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.analyzer = MahjongAnalyzer()
        
        # Состояние стола для всех игроков (включая 'me')
        self.players = {
            'me': {'hand': [], 'discards': [], 'riichi': False},
            'S': {'discards': [], 'riichi': False},
            'W': {'discards': [], 'riichi': False},
            'N': {'discards': [], 'riichi': False}
        }
        
        self.active_target = 'me'  # 'me', 'S', 'W', 'N'
        self.action_history = []  # Для кнопки «Отменить»
        
        self.tile_display_names = {
            "1z": "E", "2z": "S", "3z": "W", "4z": "N",
            "5z": "Бел", "6z": "Зел", "7z": "Крас"
        }
        
        self.winds = ["E", "S", "W", "N"]
        self.round_wind_idx = 0
        self.my_wind_idx = 0
        
        self.drag_position = None
        self.init_ui()

    def init_ui(self):
        self.main_widget = QWidget(self)
        self.main_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 25, 230);
                color: #E0E0E0;
                border-radius: 12px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QPushButton {
                background-color: rgba(60, 60, 80, 200);
                border: 1px solid #555;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover { background-color: rgba(90, 90, 120, 255); }
            QPushButton:pressed { background-color: rgba(180, 60, 80, 255); }
            QLabel { background: transparent; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self.main_widget)
        
        # === 1. ВЕРХНЯЯ ПАНЕЛЬ: ВЕТРА И СИСТЕМА ===
        top_layout = QHBoxLayout()
        
        self.round_wind_btn = QPushButton(f"Раунд: {self.winds[self.round_wind_idx]}")
        self.round_wind_btn.clicked.connect(self.cycle_round_wind)
        
        self.my_wind_btn = QPushButton(f"Мой Ветер: {self.winds[self.my_wind_idx]}")
        self.my_wind_btn.clicked.connect(self.cycle_my_wind)
        
        self.clear_btn = QPushButton("Очистить стол")
        self.clear_btn.setStyleSheet("background-color: rgba(180, 50, 50, 200);")
        self.clear_btn.clicked.connect(self.clear_table)
        
        self.exit_btn = QPushButton("❌")
        self.exit_btn.setStyleSheet("background-color: transparent; border: none; font-size: 16px;")
        self.exit_btn.clicked.connect(self.close)
        
        top_layout.addWidget(self.round_wind_btn)
        top_layout.addWidget(self.my_wind_btn)
        top_layout.addStretch()
        top_layout.addWidget(self.clear_btn)
        top_layout.addWidget(self.exit_btn)
        layout.addLayout(top_layout)
        
        # === 2. ТАКТИЧЕСКАЯ ПАНЕЛЬ: ВЫБОР ФОКУСА И РИИЧИ ===
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Куда идут клики:"))
        
        self.target_buttons = {}
        targets_info = [('me', 'Я (Рука)'), ('S', 'Игрок S'), ('W', 'Игрок W'), ('N', 'Игрок N')]
        for t_key, t_name in targets_info:
            btn = QPushButton(t_name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=t_key: self.set_active_target(k))
            target_layout.addWidget(btn)
            self.target_buttons[t_key] = btn
            
        self.target_buttons['me'].setChecked(True)
        layout.addLayout(target_layout)
        
        riichi_layout = QHBoxLayout()
        self.btn_riichi = QPushButton("📢 Объявить Риичи выбранному игроку")
        self.btn_riichi.setStyleSheet("background-color: rgba(180, 100, 30, 200);")
        self.btn_riichi.clicked.connect(self.toggle_riichi)
        riichi_layout.addWidget(self.btn_riichi)
        layout.addLayout(riichi_layout)
        
        # === 3. КРУПНЫЙ ЛОГ ИСТОРИИ И КНОПКА ОТМЕНЫ ===
        history_layout = QHBoxLayout()
        self.log_label = QLabel("📝 Лог: Стол готов к бою.")
        # Сделали текст крупнее и ярче
        self.log_label.setStyleSheet("color: #FFD700; font-size: 14px;")
        
        self.undo_btn = QPushButton("↩ Отменить")
        self.undo_btn.setFixedSize(100, 32)
        self.undo_btn.setStyleSheet("background-color: rgba(100, 60, 120, 200); font-size: 13px;")
        self.undo_btn.clicked.connect(self.undo_action)
        
        history_layout.addWidget(self.log_label, stretch=4)
        history_layout.addWidget(self.undo_btn, stretch=1)
        layout.addLayout(history_layout)
        
        # === 4. ПАЛИТРА КОСТЕЙ ===
        layout.addWidget(QLabel("Палитра костей (Кликай для добавления в выбранный фокус):"))
        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        
        suits = [
            ("Ман (m)", "m", 9),
            ("Пин (p)", "p", 9),
            ("Соу (s)", "s", 9),
            ("Ветра/Драк (z)", "z", 7)
        ]
        
        row = 0
        for suit_name, suit_char, count in suits:
            grid_layout.addWidget(QLabel(suit_name), row, 0)
            for i in range(count):
                btn_internal = f"{i+1}{suit_char}"
                display_text = self.tile_display_names.get(btn_internal, btn_internal)
                
                btn = QPushButton(display_text)
                btn.setFixedSize(45, 45)
                btn.clicked.connect(lambda checked, t=btn_internal: self.handle_palette_click(t))
                grid_layout.addWidget(btn, row, i+1)
            row += 1
        layout.addLayout(grid_layout)
        
        # === 5. МОЯ РУКА (Клик по кости в руке СБРАСЫВАЕТ её!) ===
        self.hand_label = QLabel("Моя рука (0/14) [Клик по плитке в руке = Сброс]:")
        layout.addWidget(self.hand_label)
        
        self.hand_layout = QHBoxLayout()
        self.hand_layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(self.hand_layout)
        
        # === 6. ПАНЕЛЬ СОВЕТА ===
        self.advice_label = QLabel("🔮 Совет: Добавь кости в руку, чтобы я начала расчет...")
        self.advice_label.setStyleSheet("color: #FF99BB; font-size: 13px; padding-top: 5px;")
        self.advice_label.setWordWrap(True) 
        layout.addWidget(self.advice_label)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.main_widget)
        self.setLayout(main_layout)
        self.move(100, 100)

    # Перемещение окна
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

    def cycle_round_wind(self):
        self.round_wind_idx = (self.round_wind_idx + 1) % 4
        self.round_wind_btn.setText(f"Раунд: {self.winds[self.round_wind_idx]}")

    def cycle_my_wind(self):
        self.my_wind_idx = (self.my_wind_idx + 1) % 4
        self.my_wind_btn.setText(f"Мой Ветер: {self.winds[self.my_wind_idx]}")

    def set_active_target(self, target_key):
        self.active_target = target_key
        for k, btn in self.target_buttons.items():
            btn.setChecked(k == target_key)
        target_names = {'me': 'Моя рука', 'S': 'Игрок S', 'W': 'Игрок W', 'N': 'Игрок N'}
        self.log_label.setText(f"📝 Фокус ввода: {target_names[target_key]}")

    def toggle_riichi(self):
        if self.active_target == 'me':
            self.log_label.setText("⚠️ Риичи для себя лучше объявлять в игре!")
            return
        p = self.active_target
        current_status = self.players[p]['riichi']
        self.players[p]['riichi'] = not current_status
        status_str = "ОБЪЯВИЛ РИИЧИ!" if not current_status else "снял Риичи"
        self.log_label.setText(f"📢 Игрок {p} {status_str}!")
        self.action_history.append(('toggle_riichi', p))

    def handle_palette_click(self, tile_str):
        display_tile = self.tile_display_names.get(tile_str, tile_str)
        
        if self.active_target == 'me':
            if len(self.players['me']['hand']) < 14:
                self.players['me']['hand'].append(tile_str)
                self.action_history.append(('add_me', tile_str))
                self.log_label.setText(f"📝 В руку добавлено: {display_tile}")
                self.update_ui_state()
            else:
                self.log_label.setText("⚠️ В руке уже 14 костей!")
        else:
            p = self.active_target
            self.players[p]['discards'].append(tile_str)
            self.action_history.append(('add_discard', p, tile_str))
            
            genbutsu_msg = ""
            if self.players[p]['riichi']:
                if tile_str in self.players[p]['discards'][:-1]:
                    genbutsu_msg = " [АБСОЛЮТНЫЙ ГЕНБУЦУ!]"
                else:
                    genbutsu_msg = " (Свежий сброс Риичи)"
            
            self.log_label.setText(f"💀 Игрок {p} сбросил: {display_tile}{genbutsu_msg}")
            self.update_ui_state()

    def discard_my_tile(self, index):
        """Клик по плитке в руке СБРАСЫВАЕТ её в личный сброс (учитывает Фуритен)"""
        if 0 <= index < len(self.players['me']['hand']):
            tile = self.players['me']['hand'].pop(index)
            self.players['me']['discards'].append(tile)
            self.action_history.append(('discard_me', index, tile))
            display_tile = self.tile_display_names.get(tile, tile)
            self.log_label.setText(f"🗑️ Сброшено из руки: {display_tile}")
            self.update_ui_state()

    def undo_action(self):
        if not self.action_history:
            self.log_label.setText("⚠️ Нечего отменять!")
            return
        
        last_action = self.action_history.pop()
        action_type = last_action[0]
        
        if action_type == 'add_me':
            if self.players['me']['hand']:
                removed = self.players['me']['hand'].pop()
                self.log_label.setText(f"↩ Отменено: удален {self.tile_display_names.get(removed, removed)} из руки")
        elif action_type == 'discard_me':
            _, idx, tile = last_action
            if self.players['me']['discards']:
                self.players['me']['discards'].pop() # Убираем из сброса
            self.players['me']['hand'].insert(idx, tile) # Возвращаем в руку
            self.log_label.setText(f"↩ Отменено: тайл возвращен в руку из сброса")
        elif action_type == 'add_discard':
            _, p, tile = last_action
            if self.players[p]['discards']:
                self.players['p']['discards'].pop() if 'p' in locals() else self.players[p]['discards'].pop()
                self.log_label.setText(f"↩ Отменено: убран сброс игрока {p}")
        elif action_type == 'toggle_riichi':
            _, p = last_action
            self.players[p]['riichi'] = not self.players[p]['riichi']
            self.log_label.setText(f"↩ Отменено: статус Риичи игрока {p} изменен")
            
        self.update_ui_state()

    def clear_table(self):
        for p in self.players:
            self.players[p]['hand'] = []
            self.players[p]['discards'] = []
            self.players[p]['riichi'] = False
        self.action_history.clear()
        self.update_ui_state()
        self.log_label.setText("🔮 Стол полностью очищен. Новая партия!")

    def update_ui_state(self):
        hand = self.players['me']['hand']
        self.hand_label.setText(f"Моя рука ({len(hand)}/14) [Клик по плитке = Сброс]:")
        
        for i in reversed(range(self.hand_layout.count())): 
            widget = self.hand_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
                
        # Рендерим руку: клик по любой кости теперь её СБРАСЫВАЕТ!
        for idx, tile in enumerate(hand):
            display_text = self.tile_display_names.get(tile, tile)
            btn = QPushButton(display_text)
            btn.setFixedSize(45, 60)
            btn.setStyleSheet("background-color: rgba(90, 150, 90, 200); color: white;")
            btn.clicked.connect(lambda checked, i=idx: self.discard_my_tile(i))
            self.hand_layout.addWidget(btn)
            
        # Собираем ВСЕ сбросы на столе (мои + оппонентов) для точного расчета Укеире и Фуритена
        all_table_discards = list(self.players['me']['discards'])
        for p in ['S', 'W', 'N']:
            all_table_discards.extend(self.players[p]['discards'])
            
        if len(hand) in [14, 11, 8, 5]:
            hand_str = "".join(hand)
            advice = self.analyzer.analyze_hand(hand_str, all_table_discards, self.players['me']['discards'])
            self.advice_label.setText(advice)
        else:
            self.advice_label.setText("🔮 Жду нужного количества костей для расчета...")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AlphaJongCompanion()
    window.show()
    sys.exit(app.exec_())