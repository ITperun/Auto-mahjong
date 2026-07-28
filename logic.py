from mahjong.shanten import Shanten
from mahjong.tile import TilesConverter

class MahjongAnalyzer:
    def __init__(self):
        self.shanten_calculator = Shanten()

    def analyze_hand(self, tiles_string, all_discards_list, my_discards_list=None):
        try:
            tiles_34 = TilesConverter.one_line_string_to_34_array(tiles_string)
            current_shanten = self.shanten_calculator.calculate_shanten(tiles_34)
            
            if current_shanten == -1:
                return "✨ ЦУМО! Рука уже идеальна, забирай их души! ✨"
            
            # Все видимые кости на столе (моя рука + все сбросы на столе)
            visible_tiles = list(tiles_34) 
            
            if all_discards_list:
                discards_string = "".join(all_discards_list)
                discards_34 = TilesConverter.one_line_string_to_34_array(discards_string)
                for i in range(34):
                    visible_tiles[i] += discards_34[i]
                    
            # Переводим мои сбросы в массив для проверки Фуритена
            my_discards_34 = None
            if my_discards_list:
                my_str = "".join(my_discards_list)
                if my_str:
                    my_discards_34 = TilesConverter.one_line_string_to_34_array(my_str)
            
            best_discards = []
            max_ukeire = -1 
            in_furiten = False
            
            for i in range(34):
                if tiles_34[i] > 0:
                    tiles_34[i] -= 1
                    new_shanten = self.shanten_calculator.calculate_shanten(tiles_34)
                    
                    if new_shanten == current_shanten:
                        ukeire_count = 0
                        waits = []
                        
                        for j in range(34):
                            if visible_tiles[j] < 4:
                                tiles_34[j] += 1
                                shanten_after_draw = self.shanten_calculator.calculate_shanten(tiles_34)
                                tiles_34[j] -= 1
                                
                                if shanten_after_draw < current_shanten:
                                    remaining = 4 - visible_tiles[j]
                                    ukeire_count += remaining
                                    tile_name = self._index_to_tile_name(j)
                                    waits.append(tile_name)
                                    
                                    # ПРОВЕРКА ФУРИТЕНА: если нужная кость есть в моем личном сбросе!
                                    if my_discards_34 and my_discards_34[j] > 0:
                                        in_furiten = True
                        
                        if ukeire_count > max_ukeire:
                            max_ukeire = ukeire_count
                            best_discards = [(i, ukeire_count, waits)]
                        elif ukeire_count == max_ukeire:
                            best_discards.append((i, ukeire_count, waits))
                            
                    tiles_34[i] += 1
            
            if not best_discards or max_ukeire == 0:
                return f"🔮 Шантен: {current_shanten}. 💀 Мертвый конец. Живых костей больше нет!"
            
            status = ""
            if in_furiten:
                status += "⚠️ ВНИМАНИЕ: ФУРИТЕН! (Победная кость в вашем сбросе!)\n"
                
            status += f"🔮 Шагов до победы (Шантен): {current_shanten}.\n🎯 Идеальный сброс:\n"
            for tile_idx, ukeire, waits in best_discards:
                tile_name = self._index_to_tile_name(tile_idx)
                waits_str = ", ".join(waits)
                status += f"   • {tile_name} (Ждем {ukeire} шт: {waits_str})\n"
            
            return status
                
        except Exception as e:
            return f"Ой... Моя магия споткнулась. Ошибка: {e}"

    def _index_to_tile_name(self, index):
        if index < 9: return f"{index + 1}m"
        elif index < 18: return f"{index - 9 + 1}p"
        elif index < 27: return f"{index - 18 + 1}s"
        else:
            honors = ["Восток", "Юг", "Запад", "Север", "Белый Драк.", "Зел. Драк.", "Кр. Драк."]
            return honors[index - 27]