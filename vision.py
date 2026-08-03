import cv2
import numpy as np
import mss
import os

class TableEye:
    def __init__(self, templates_dir="templates", threshold=0.65):
        # 💡 Порог 0.65 — идеальный стандарт под Mahjong Soul
        self.templates_dir = templates_dir
        self.threshold = threshold
        self.templates = {}
        # 💡 3 снайперских масштаба для работы без зависаний
        self.scales = [0.97, 1.0, 1.03]
        self.load_templates()

    def load_templates(self):
        """Безопасная загрузка шаблонов с поддержкой кириллицы в путях Windows"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            print(f"⚠️ Папка {self.templates_dir} создана. Наполни её шаблонами Mahjong Soul (.png)!")
            return

        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".png"):
                tile_name = os.path.splitext(filename)[0]
                path = os.path.join(self.templates_dir, filename)
                img_array = np.fromfile(path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    self.templates[tile_name] = img

        print(f"✨ Загружено шаблонов Mahjong Soul в память: {len(self.templates)}")

    def _grab_region(self, monitor_box):
        with mss.mss() as sct:
            sct_img = sct.grab(monitor_box)
            img = np.array(sct_img)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def scan_area(self, monitor_box, remove_overlap_px=52, debug_name=None):
        if not self.templates:
            return []

        screen_img = self._grab_region(monitor_box)
        screen_h, screen_w = screen_img.shape[:2]
        detections = []

        for tile_name, template in self.templates.items():
            orig_h, orig_w = template.shape[:2]

            for scale in self.scales:
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)

                if screen_h < new_h or screen_w < new_w or new_w <= 0 or new_h <= 0:
                    continue

                scaled_tpl = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)
                result = cv2.matchTemplate(screen_img, scaled_tpl, cv2.TM_CCOEFF_NORMED)
                
                yloc, xloc = np.where(result >= self.threshold)

                for x, y in zip(xloc, yloc):
                    conf = result[y, x]
                    
                    # 💡 ЛИСЬЯ ЗАЩИТА: 
                    # 1. Белый Дракон (5z) требует строгого порога 0.83 (против облаков)
                    if tile_name == "5z" and conf < 0.83:
                        continue
                    # 2. Красные пятёрки (5ap, 5am, 5as) требуют порога 0.88,
                    # чтобы не путаться с обычными пятёрками!
                    if tile_name in ["5ap", "5am", "5as"] and conf < 0.88:
                        continue
                        
                    detections.append((int(x), int(y), new_w, new_h, float(conf), tile_name))

        if not detections:
            return []

        # === ГОРИЗОНТАЛЬНАЯ ГИЛЬОТИНА (1D Non-Maximum Suppression) ===
        # Самые уверенные совпадения вытесняют слабые копии!
        detections.sort(key=lambda d: d[4], reverse=True)
        filtered = []

        for x, y, tw, th, conf, name in detections:
            is_overlap = False
            for fx, fy, ftw, fth, fconf, fname in filtered:
                # 💡 remove_overlap_px = 52 гарантирует, что на ширине одной плитки
                # выживет ТОЛЬКО ОДИН самый точный шаблон (убивает фантомы 4s внутри 6s!)
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

        # Сортируем тайлы строго слева направо по координате X
        filtered.sort(key=lambda d: d[0])
        return [name for _, _, _, _, _, name in filtered]

    def scan_my_hand(self, screen_w=1920, screen_h=1080):
        """
        💡 Оконный режим (Steam + Панель задач Windows):
        Захватываем руку с запасом по ширине (remove_overlap_px = 52)
        """
        hand_box = {
            "top": int(screen_h * 0.75),
            "left": int(screen_w * 0.13),
            "width": int(screen_w * 0.73),
            "height": int(screen_h * 0.18)
        }
        return self.scan_area(hand_box, remove_overlap_px=52, debug_name="debug_eye.png")

    def scan_dora_box(self, screen_w=1920, screen_h=1080):
        """
        💡 Индикатор Доры под шапкой окна Steam
        """
        dora_box = {
            "top": int(screen_h * 0.06),
            "left": int(screen_w * 0.01),
            "width": int(screen_w * 0.15),
            "height": int(screen_h * 0.14)
        }
        return self.scan_area(dora_box, remove_overlap_px=35)