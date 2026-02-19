"""
AI сервис для прогнозирования
"""
from typing import List


class AIService:
    """Сервис AI прогнозов"""
    
    @staticmethod
    def predict_linear(data_points: List[float], steps_ahead: int = 1) -> float:
        """
        Линейная регрессия для прогноза
        
        Args:
            data_points: Список исторических значений
            steps_ahead: На сколько шагов вперед прогноз
            
        Returns:
            Прогнозируемое значение
        """
        if len(data_points) < 5:
            return data_points[-1] if data_points else 0.0
        
        n = len(data_points)
        sum_x = sum_y = sum_xy = sum_xx = 0
        
        for i in range(n):
            sum_x += i
            sum_y += data_points[i]
            sum_xy += i * data_points[i]
            sum_xx += i * i
        
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator == 0:
            return round(data_points[-1], 1)

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Прогноз на N шагов вперед
        steps = max(1, int(steps_ahead))
        prediction = slope * (n + steps) + intercept
        
        return round(prediction, 1)
    
    @staticmethod
    def calculate_mc_score(current_data: dict, profile: dict) -> int:
        """
        Расчет MicroClimate Score (0-100)
        
        Args:
            current_data: Текущие данные
            profile: Активный профиль
            
        Returns:
            MC Score от 0 до 100
        """
        if current_data["timestamp"] is None:
            return 0
        
        score = 100
        temp = current_data["temperature"]
        hum = current_data["humidity"]
        co2 = current_data["co2_ppm"]
        co = current_data["co_ppm"]
        lux = current_data["lux"]
        
        # Штрафы за выход из нормы
        if temp < profile["temp_min"] or temp > profile["temp_max"]:
            score -= 15
        if hum > profile["humidity_max"]:
            score -= 15
        if co2 > profile["co2_max"]:
            score -= 20
        co_max = profile.get("co_max")
        if co_max is not None and co > co_max:
            score -= 25
        if lux < profile["lux_min"] or lux > profile["lux_max"]:
            score -= 10
        
        return max(0, min(100, score))


# Глобальный экземпляр сервиса
ai_service = AIService()
