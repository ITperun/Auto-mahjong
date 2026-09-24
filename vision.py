import cv2
import numpy as np
import mss
import os

class TableEye:
    def __init__(self, templates_dir="templates", threshold=0.65):
        # 💡 Порог 0.65 — наш идеальный, проверенный стандарт для Mahjong Soul
        self.templates_dir = templates_dir
        self.threshold = threshold
        # 💡 Снайперская тройка масштабов
        self.scales = [0.98, 1.0, 1.02]
        
        # 💡 КЭШ ШАБЛОНОВ В ПАМЯТИ: [(tile_name, scaled_img, width, height), ...]
        # Мы рассчитаем размеры один раз при старте, чтобы не тормозить при клике!
        self.cached_templates = []
        self.load_templates()

    def load_templates(self):
        """
        Безопасная загрузка шаблонов с кириллицей в путях Windows
        + МГНОВЕННОЕ ПРЕДВАРИТЕЛЬНОЕ МАСШТАБИРОВАНИЕ В ПАМЯТИ (Pre-scaling).
        """
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            print(f"⚠️ Папка {self.templates_dir} создана. Наполни её шаблонами (.png)!")
            return

        self.cached_templates.clear()
        loaded_count = 0

        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".png"):
                tile_name = os.path.splitext(filename)[0]
                path = os.path.join(self.templates_dir, filename)
                img_array = np.fromfile(path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if img is not None:
                    loaded_count += 1
                    orig_h, orig_w = img.shape[:2]
                    
                    # 💡 Сразу генерируем все нужные масштабы и складываем в оперативную память
                    for scale in self.scales:
                        new_w = int(orig_w * scale)
                        new_h = int(orig_h * scale)
                        if new_w > 0 and new_h > 0:
                            scaled_tpl = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                            self.cached_templates.append((tile_name, scaled_tpl, new_w, new_h))

        print(f"✨ Загружено базовых шаблонов: {loaded_count} | В кэше скорости (с масштабами): {len(self.cached_templates)}")

    def _grab_region(self, monitor_box):
        """Быстрый захват экрана через mss -> BGR"""
        with mss.mss() as sct:
            sct_img = sct.grab(monitor_box)
            img = np.array(sct_img)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def scan_area(self, monitor_box, remove_overlap_px=52, debug_name=None):
        if not self.cached_templates:
            return []

        screen_img = self._grab_region(monitor_box)
        screen_h, screen_w = screen_img.shape[:2]
        detections = []

        # === МОЛНИЕНОСНЫЙ ПРОХОД ПО ГОТОВОМУ КЭШУ ===
        # Больше никаких cv2.resize() внутри цикла сканирования!
        for tile_name, scaled_tpl, tw, th in self.cached_templates:
            if screen_h < th or screen_w < tw:
                continue

            result = cv2.matchTemplate(screen_img, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            yloc, xloc = np.where(result >= self.threshold)

            for x, y in zip(xloc, yloc):
                conf = result[y, x]
                
                # 💡 ЛИСЬЯ ЗАЩИТА ОТ ИЛЛЮЗИЙ:
                # 1. Белый Дракон (5z) требует строгого порога 0.83
                if tile_name == "5z" and conf < 0.83:
                    continue
                # 2. Красные пятерки требуют порога 0.88, чтобы не путаться с обычными
                if tile_name in ["5ap", "5am", "5as"] and conf < 0.88:
                    continue
                    
                detections.append((int(x), int(y), tw, th, float(conf), tile_name))

        if not detections:
            return []

        # === ГОРИЗОНТАЛЬНАЯ ГИЛЬОТИНА (1D Non-Maximum Suppression) ===
        detections.sort(key=lambda d: d[4], reverse=True)
        filtered = []

        for x, y, tw, th, conf, name in detections:
            is_overlap = False
            for fx, fy, ftw, fth, fconf, fname in filtered:
                if abs(x - fx) < remove_overlap_px:
                    is_overlap = True
                    break
            if not is_overlap:
                filtered.append((x, y, tw, th, conf, name))

        if debug_name:
            debug_img = screen_img.copy()
            print(f"\n--- 👁️ Отчет сканирования Mahjong Soul ({debug_name}) ---")
            for x, y, tw, th, conf, name in sorted(filtered, key=lambda d: d[0]):
                print(f"  [+] Найдено: {name:<5} | Уверенность: {conf:.2f} | X: {x}")
                cv2.rectangle(debug_img, (x, y), (x + tw, y + th), (0, 255, 0), 2)
                cv2.putText(debug_img, f"{name} ({conf:.2f})", (x, max(12, y - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            cv2.imwrite(debug_name, debug_img)
            print("---------------------------------------------------------")

        filtered.sort(key=lambda d: d[0])
        return [name for _, _, _, _, _, name in filtered]

    def scan_my_hand(self, screen_w=1920, screen_h=1080):
        """💡 Оконный режим (Steam + Панель задач Windows)"""
        hand_box = {
            "top": int(screen_h * 0.75),
            "left": int(screen_w * 0.13),
            "width": int(screen_w * 0.73),
            "height": int(screen_h * 0.18)
        }
        return self.scan_area(hand_box, remove_overlap_px=52, debug_name="debug_eye.png")

    def scan_dora_box(self, screen_w=1920, screen_h=1080):
        """💡 Индикатор Доры в левом верхнем углу"""
        dora_box = {
            "top": int(screen_h * 0.06),
            "left": int(screen_w * 0.01),
            "width": int(screen_w * 0.15),
            "height": int(screen_h * 0.14)
        }
        return self.scan_area(dora_box, remove_overlap_px=35)