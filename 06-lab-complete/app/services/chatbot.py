"""
Travel chatbot service.

Dùng OpenAI nếu có OPENAI_API_KEY, ngược lại fallback sang rule-based
assistant tích hợp sẵn (chạy offline, không cần API key).
"""
import logging
from typing import Dict, List

from app.config import settings

logger = logging.getLogger("travel-chatbot")

SYSTEM_PROMPT = """You are TravelBot, an expert AI travel assistant for the
Day5-6 Hackathon Travel application. You help users plan trips, recommend
destinations, suggest hotels, restaurants, activities, and provide travel tips.
Always respond in the same language the user writes in (Vietnamese or English).
Keep answers friendly, concise and helpful."""

FALLBACK_RESPONSES = {
    "xin chào": "Xin chào! Tôi là TravelBot 🌍 Tôi có thể giúp bạn lên kế hoạch du lịch, gợi ý điểm đến, khách sạn và nhiều hơn nữa. Bạn muốn đi đâu?",
    "hello": "Hello! I'm TravelBot 🌍 I can help you plan trips, find destinations, hotels and activities. Where would you like to go?",
    "hi": "Hi there! I'm TravelBot 🌍 Ready to help you plan your next adventure. Where are you thinking of traveling?",
    "hà nội": "Hà Nội là thủ đô ngàn năm văn hiến của Việt Nam! 🏛️\n\n**Điểm tham quan nổi bật:**\n- Hồ Hoàn Kiếm & Tháp Rùa\n- Văn Miếu Quốc Tử Giám\n- Phố cổ 36 phố phường\n- Lăng Bác Hồ\n\n**Ẩm thực phải thử:**\n- Phở Bát Đàn\n- Bún chả Hương Liên\n- Chả cá Lã Vọng\n\nBạn dự định đi mấy ngày?",
    "đà nẵng": "Đà Nẵng – thành phố đáng sống! 🌊\n\n**Điểm nổi bật:**\n- Bãi biển Mỹ Khê (top 6 bãi biển đẹp thế giới)\n- Cầu Rồng phun lửa (cuối tuần)\n- Bà Nà Hills & Cầu Vàng\n- Phố cổ Hội An (30 phút)\n\n**Thời điểm tốt nhất:** Tháng 1–8\n\nBạn muốn biết thêm về khách sạn hay hoạt động?",
    "hội an": "Hội An – Phố cổ huyền diệu! 🏮\n\n**Không thể bỏ qua:**\n- Phố đèn lồng Hội An\n- Chùa Cầu Nhật Bản\n- Làng rau Trà Quế\n- Lăng Mộ & Nhà cổ\n\n**Ẩm thực đặc sắc:**\n- Cao lầu\n- Mì Quảng\n- Bánh mì Phượng\n\nThích chụp ảnh? Đến lễ hội đèn lồng vào 14 âm lịch nhé!",
    "sapa": "Sa Pa – Vùng cao mây phủ! 🏔️\n\n**Trải nghiệm:**\n- Trekking Fansipan (3143m – Nóc nhà Đông Dương)\n- Ruộng bậc thang Mù Cang Chải (tháng 9-10)\n- Bản làng người H'Mông, Dao Đỏ\n- Chợ phiên Bắc Hà\n\n**Lưu ý:** Mang áo ấm, nhiệt độ có thể 5°C vào mùa đông.\n\nBạn muốn đặt tour trekking không?",
    "phú quốc": "Phú Quốc – Đảo Ngọc Việt Nam! 🌴\n\n**Điểm đến:**\n- Bãi Sao, Bãi Dài, Bãi Trường\n- VinWonders & Safari\n- Chợ đêm Dinh Cậu\n- Làng chài Hàm Ninh\n\n**Đặc sản:** Nước mắm Phú Quốc, Nhum biển, Ghẹ hấp\n\n**Bay từ HCM:** ~1 giờ | Từ HN: ~2 giờ\n\nMùa đẹp nhất: Tháng 11 – tháng 4.",
    "bangkok": "Bangkok – City of Angels! 🛕\n\n**Must-see:**\n- Grand Palace & Wat Phra Kaew\n- Wat Arun (Temple of Dawn)\n- Chatuchak Weekend Market\n- Khao San Road\n- Floating Markets\n\n**Food:** Pad Thai, Tom Yum, Mango Sticky Rice\n\n**Getting around:** BTS Skytrain, MRT, Grab\n\nHow many days are you planning?",
    "paris": "Paris – The City of Light! 🗼\n\n**Must-see:**\n- Eiffel Tower\n- Louvre Museum\n- Notre-Dame Cathedral\n- Montmartre & Sacré-Cœur\n- Seine River Cruise\n\n**Food:** Croissants, Crêpes, French onion soup\n\n**Best time:** April–June, Sept–Oct\n\nWould you like hotel or restaurant recommendations?",
    "tokyo": "Tokyo – Where tradition meets future! 🗾\n\n**Top spots:**\n- Shibuya Crossing\n- Senso-ji Temple (Asakusa)\n- Shinjuku & Harajuku\n- teamLab Borderless\n- Mount Fuji day trip\n\n**Food:** Ramen, Sushi, Yakitori, Wagyu\n\n**Best time:** March–April (Cherry blossom) or Nov\n\nNeed a Tokyo itinerary?",
}


def _rule_based_reply(user_message: str) -> str | None:
    msg = user_message.lower().strip()
    for key, value in FALLBACK_RESPONSES.items():
        if key in msg:
            return value
    # generic travel keywords
    if any(w in msg for w in ["du lịch", "travel", "trip", "tour", "hotel", "khách sạn"]):
        return (
            "Tôi có thể giúp bạn khám phá các điểm đến tuyệt vời! 🌏\n\n"
            "Hãy cho tôi biết:\n"
            "1. Bạn muốn đi **đâu**?\n"
            "2. Thời gian **bao lâu**?\n"
            "3. Ngân sách **khoảng bao nhiêu**?\n\n"
            "Tôi sẽ gợi ý lịch trình phù hợp nhất cho bạn!"
        )
    return None


async def get_travel_response(history: List[Dict[str, str]]) -> str:
    if settings.llm_mode == "openai":
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=800,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:  # pragma: no cover - cần API key thật để hit
            logger.warning('{"event":"openai_error","detail":"%s"}' % str(e))

    # Fallback: rule-based
    last_user_msg = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )
    reply = _rule_based_reply(last_user_msg)
    if reply:
        return reply

    return (
        "Xin lỗi, tôi chưa có thông tin về chủ đề này. 😊\n\n"
        "Tôi có thể tư vấn về các điểm đến phổ biến như:\n"
        "🇻🇳 **Việt Nam:** Hà Nội, Đà Nẵng, Hội An, Sapa, Phú Quốc\n"
        "🌏 **Châu Á:** Bangkok, Tokyo, Bali, Singapore\n"
        "🌍 **Châu Âu:** Paris, Rome, Barcelona\n\n"
        "Bạn muốn khám phá điểm đến nào?"
    )
