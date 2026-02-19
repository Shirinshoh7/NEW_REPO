"""
API маршруты для истории
"""
from fastapi import APIRouter
from ...core.storage import storage
from ...services.ai_service import ai_service

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def get_history(limit: int = 50):
    history_data = storage.get_history(limit)
    profile = storage.active_profile  # активный профиль

    enriched = []
    for item in history_data:
        # поддержка разных ключей (на всякий)
        temp = float(item.get("temp", item.get("temperature", 0)))
        hum = float(item.get("hum", item.get("humidity", 0)))
        co2 = float(item.get("co2", item.get("co2_ppm", 0)))
        co = float(item.get("co", item.get("co_ppm", 0)))
        lux = float(item.get("lux", 0))

        issues = []

        if temp < profile["temp_min"] or temp > profile["temp_max"]:
            issues.append("temperature")
        if hum > profile["humidity_max"]:
            issues.append("humidity")
        if co2 > profile["co2_max"]:
            issues.append("co2_ppm")
        co_max = profile.get("co_max")
        if co_max is not None and co > co_max:
            issues.append("co_ppm")
        if lux < profile["lux_min"] or lux > profile["lux_max"]:
            issues.append("lux")

        mc_score = ai_service.calculate_mc_score(
            {
                "temperature": temp,
                "humidity": hum,
                "co2_ppm": co2,
                "co_ppm": co,
                "lux": lux,
                "timestamp": item.get("time") or item.get("timestamp") or "ok",
            },
            profile,
        )

        row = dict(item)
        row["mc_score"] = mc_score
        row["is_danger"] = len(issues) > 0
        row["issues"] = issues
        row["status"] = "out_of_range" if issues else "ok"
        row["message"] = "Вне нормы" if issues else "Норма"

        enriched.append(row)

    return {"count": len(enriched), "profile": profile["name"], "data": enriched}
