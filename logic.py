from mahjong.shanten import Shanten
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.meld import Meld
from mahjong.constants import EAST, SOUTH, WEST, NORTH

class MahjongAnalyzer:
    def __init__(self):
        self.shanten_calculator = Shanten()
        self.hand_calculator = HandCalculator()

    def _to_34_idx(self, tile_str):
        if tile_str[0] == '0':
            val = 4 
        else:
            val = int(tile_str[0]) - 1
            
        suit = tile_str[1]
        if suit == 'm': return val
        if suit == 'p': return val + 9
        if suit == 's': return val + 18
        if suit == 'z': return val + 27
        return 0

    def _get_136_id(self, tile_str, used_136):
        idx = self._to_34_idx(tile_str)
        base = idx * 4
        
        if tile_str in ['0m', '0p', '0s']:
            if base not in used_136:
                used_136.add(base)
                return base
                
        for offset in range(1, 4) if tile_str in ['5m', '5p', '5s'] else range(4):
            candidate = base + offset
            if candidate not in used_136:
                used_136.add(candidate)
                return candidate
                
        for offset in range(4):
            candidate = base + offset
            if candidate not in used_136:
                used_136.add(candidate)
                return candidate
        return base

    def _list_to_34_array(self, tile_list):
        res = [0] * 34
        for t in tile_list:
            res[self._to_34_idx(t)] += 1
        return res

    def _index_to_internal_name(self, index):
        if index < 9: return f"{index + 1}m"
        elif index < 18: return f"{index - 9 + 1}p"
        elif index < 27: return f"{index - 18 + 1}s"
        else: return f"{index - 27 + 1}z"

    def analyze_hand(self, hand_list, all_discards_list, my_discards_list, melds_data, round_wind, player_wind, dora_indicators_list):
        try:
            tiles_34 = self._list_to_34_array(hand_list)
            open_sets_count = 0
            melds_tiles_list = []
            
            if melds_data:
                for m_type, m_tiles in melds_data:
                    melds_tiles_list.extend(m_tiles)
                    if m_type in ["Пон", "Чи", "Кан", "Закр. Кан"]:
                        open_sets_count += 1

            current_shanten = self.shanten_calculator.calculate_shanten(tiles_34, open_sets_count)
            
            if current_shanten == -1:
                return "✨ ЦУМО! Рука уже идеальна, забирай их души! ✨"
            
            visible_tiles = list(tiles_34) 
            discards_34 = self._list_to_34_array(all_discards_list)
            for i in range(34): visible_tiles[i] += discards_34[i]
                
            melds_34 = self._list_to_34_array(melds_tiles_list)
            for i in range(34): visible_tiles[i] += melds_34[i]
                
            my_discards_34 = self._list_to_34_array(my_discards_list) if my_discards_list else None
            
            best_discards = []
            max_ukeire = -1 
            in_furiten = False
            
            config = HandConfig(
                is_tsumo=True, 
                round_wind=round_wind, 
                player_wind=player_wind, 
                options=OptionalRules(has_aka_dora=True)
            )
            
            for i in range(34):
                if tiles_34[i] > 0:
                    tiles_34[i] -= 1
                    new_shanten = self.shanten_calculator.calculate_shanten(tiles_34, open_sets_count)
                    
                    if new_shanten == current_shanten:
                        ukeire_count = 0
                        waits = []
                        yaku_info = []
                        
                        for j in range(34):
                            if visible_tiles[j] < 4:
                                tiles_34[j] += 1
                                shanten_after_draw = self.shanten_calculator.calculate_shanten(tiles_34, open_sets_count)
                                
                                if shanten_after_draw < current_shanten:
                                    remaining = 4 - visible_tiles[j]
                                    ukeire_count += remaining
                                    tile_name = self._index_to_tile_name(j)
                                    
                                    if current_shanten == 0:
                                        used_136 = set()
                                        simulated_melds = []
                                        
                                        if melds_data:
                                            for m_type, m_tiles in melds_data:
                                                m_136 = [self._get_136_id(t, used_136) for t in m_tiles]
                                                if m_type == "Пон": simulated_melds.append(Meld(Meld.PON, m_136))
                                                elif m_type == "Чи": simulated_melds.append(Meld(Meld.CHI, m_136))
                                                elif m_type == "Кан": simulated_melds.append(Meld(Meld.KAN, m_136, True))
                                                elif m_type == "Закр. Кан": simulated_melds.append(Meld(Meld.KAN, m_136, False))

                                        tiles_136 = []
                                        temp_34 = list(tiles_34)
                                        temp_34[j] -= 1 # Устраняем дублирование победной кости
                                        
                                        for t_str in hand_list:
                                            if t_str in ['0m', '0p', '0s']:
                                                idx = self._to_34_idx(t_str)
                                                if temp_34[idx] > 0:
                                                    tiles_136.append(self._get_136_id(t_str, used_136))
                                                    temp_34[idx] -= 1
                                        
                                        for k in range(34):
                                            for _ in range(temp_34[k]):
                                                dummy_str = f"5m" if k == 4 else (f"5p" if k == 13 else (f"5s" if k == 22 else self._index_to_internal_name(k)))
                                                tiles_136.append(self._get_136_id(dummy_str, used_136))
                                                
                                        win_tile_136 = self._get_136_id(self._index_to_internal_name(j), used_136)
                                        tiles_136.append(win_tile_136)
                                        
                                        dora_136 = [self._get_136_id(d, used_136) for d in dora_indicators_list]

                                        try:
                                            result = self.hand_calculator.estimate_hand_value(tiles_136, win_tile_136, simulated_melds, dora_136, config)
                                            if result.error:
                                                if result.error == "There are no yaku in the hand":
                                                    yaku_info.append(f"{tile_name} (Ёку - НЕТ ЯКУ!)")
                                                else:
                                                    yaku_info.append(f"{tile_name} (Ошибка: {result.error})")
                                            else:
                                                yaku_names = ", ".join([yaku.name for yaku in result.yaku])
                                                yaku_info.append(f"{tile_name} [{result.han} Хан, {result.fu} Фу | {yaku_names}]")
                                        except Exception as ex:
                                            yaku_info.append(f"{tile_name} (Ошибка оценки Яку)")
                                    else:
                                        waits.append(tile_name)
                                        
                                    if my_discards_34 and my_discards_34[j] > 0:
                                        in_furiten = True
                                        
                                tiles_34[j] -= 1
                                
                        if ukeire_count > max_ukeire:
                            max_ukeire = ukeire_count
                            best_discards = [(i, ukeire_count, waits, yaku_info)]
                        elif ukeire_count == max_ukeire:
                            best_discards.append((i, ukeire_count, waits, yaku_info))
                            
                    tiles_34[i] += 1
            
            def get_discard_name(idx):
                for t_str in hand_list:
                    if self._to_34_idx(t_str) == idx:
                        if t_str in ['0m', '0p', '0s']: return "🔴" + t_str[1:] 
                return self._index_to_tile_name(idx)

            if not best_discards or max_ukeire <= 0:
                return f"🔮 Шантен: {current_shanten}. 💀 Осторожно: этот сброс оставляет тебя без живых ожиданий!"
            
            status = ""
            if in_furiten:
                status += "⚠️ ВНИМАНИЕ: ФУРИТЕН! (Победная кость в вашем сбросе!)\n"
                
            status += f"🔮 Шагов до победы (Шантен): {current_shanten} (Открытых сетов: {open_sets_count}).\n"
            status += "🎯 Оценка действий (Сброс -> Ожидание):\n"
            
            for tile_idx, ukeire, waits, yaku_info in best_discards:
                discard_name = get_discard_name(tile_idx)
                if current_shanten == 0:
                    yaku_str = "\n      ↳ ".join(yaku_info)
                    status += f"   • Сбрось {discard_name} (Ждем {ukeire} шт):\n      ↳ {yaku_str}\n"
                else:
                    waits_str = ", ".join(waits)
                    status += f"   • Сбрось {discard_name} (Улучшают {ukeire} шт: {waits_str})\n"
            
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