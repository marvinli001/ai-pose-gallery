"""
AI服务 - 图片分析和标签生成
"""
import base64
import httpx
from typing import List, Dict, Any
from PIL import Image
import io
import json

from app.config import get_settings
from app.models.image import TagCategory

settings = get_settings()


class AIService:
    """AI服务类"""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        
    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """分析图片并生成标签和描述"""
        try:
            # 加载和处理图片
            image_data = self._prepare_image(image_path)
            
            # 如果没有配置OpenAI API Key，使用模拟分析
            if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
                return self._mock_analysis(image_path)
            
            # 调用OpenAI Vision API
            return await self._call_openai_vision(image_data)
            
        except Exception as e:
            print(f"❌ 图片分析失败: {e}")
            return self._get_fallback_analysis()
    
    def _prepare_image(self, image_path: str) -> str:
        """准备图片数据用于AI分析"""
        try:
            # 打开图片
            with Image.open(image_path) as img:
                # 转换为RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整大小以节省API费用
                max_size = 1024
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # 转换为base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                image_bytes = buffer.getvalue()
                
                return base64.b64encode(image_bytes).decode('utf-8')
                
        except Exception as e:
            print(f"❌ 图片预处理失败: {e}")
            raise
    
    async def _call_openai_vision(self, image_data: str) -> Dict[str, Any]:
        """调用OpenAI Vision API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}"
        }
        
        prompt = """请分析这张图片中的人物姿势和场景，并提供以下信息：

1. 详细描述图片内容（100字以内）
2. 提取相关标签，包括：
   - 姿势类型（如：站姿、坐姿、躺姿、蹲姿）
   - 性别（如：男性、女性）
   - 年龄段（如：儿童、青年、中年、老年）
   - 服装（如：正装、休闲装、裙子）
   - 道具（如：椅子、桌子、书本、咖啡杯、无道具）
   - 场景（如：室内、户外、办公室、家居）
   - 光线（如：自然光、人工光、柔和光、强光）
   - 角度（如：正面、侧面、背面、俯视、仰视）
   - 表情（如：微笑、严肃、思考、放松）
   - 动作（如：站立、行走、阅读、思考、伸展）

请以JSON格式返回，格式如下：
{
    "description": "图片描述",
    "tags": ["标签1", "标签2", ...],
    "confidence": 0.85
}"""

        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }
        
        try:
            response = await self.client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 尝试解析JSON
                try:
                    analysis = json.loads(content)
                    return analysis
                except json.JSONDecodeError:
                    # 如果不是JSON格式，尝试从文本中提取
                    return self._parse_text_response(content)
            else:
                print(f"❌ OpenAI API错误: {response.status_code} - {response.text}")
                return self._get_fallback_analysis()
                
        except Exception as e:
            print(f"❌ OpenAI API调用失败: {e}")
            return self._get_fallback_analysis()
    
    def _mock_analysis(self, image_path: str) -> Dict[str, Any]:
        """模拟AI分析（用于演示）"""
        print("🤖 使用模拟AI分析（未配置OpenAI API Key）")
        
        import random
        from pathlib import Path
        
        filename = Path(image_path).name.lower()
        
        # 根据文件名推测内容
        tags = []
        description = "人物姿势参考图片"
        
        # 基础标签
        tags.extend(random.choices(["女性", "男性"], k=1))
        tags.extend(random.choices(["青年", "中年"], k=1))
        tags.extend(random.choices(["站姿", "坐姿", "躺姿"], k=1))
        tags.extend(random.choices(["正面", "侧面", "背面"], k=1))
        tags.extend(random.choices(["室内", "户外"], k=1))
        tags.extend(random.choices(["自然光", "人工光"], k=1))
        tags.extend(random.choices(["休闲装", "正装"], k=1))
        
        # 根据文件名添加特定标签
        if any(word in filename for word in ["sit", "chair", "坐"]):
            tags.append("坐姿")
            tags.append("椅子")
            description = "人物坐姿参考，适合插画和摄影参考"
        elif any(word in filename for word in ["stand", "站"]):
            tags.append("站姿")
            description = "人物站姿参考，展现自然站立姿态"
        
        if any(word in filename for word in ["outdoor", "park", "户外"]):
            tags.extend(["户外", "自然光"])
            description += "，户外环境拍摄"
        
        # 去重
        tags = list(set(tags))
        
        return {
            "description": description,
            "tags": tags[:8],  # 最多8个标签
            "confidence": round(random.uniform(0.75, 0.95), 2)
        }
    
    def _parse_text_response(self, content: str) -> Dict[str, Any]:
        """从文本响应中解析分析结果"""
        # 简单的文本解析逻辑
        lines = content.split('\n')
        description = ""
        tags = []
        
        for line in lines:
            if "描述" in line or "description" in line.lower():
                description = line.split(':', 1)[-1].strip()
            elif "标签" in line or "tags" in line.lower() or "tag" in line.lower():
                # 提取标签
                tag_part = line.split(':', 1)[-1].strip()
                tags.extend([tag.strip() for tag in tag_part.split(',') if tag.strip()])
        
        return {
            "description": description or "AI分析的人物姿势图片",
            "tags": tags[:10],
            "confidence": 0.8
        }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """获取备用分析结果"""
        return {
            "description": "人物姿势参考图片",
            "tags": ["人物", "姿势", "参考"],
            "confidence": 0.5
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 创建全局AI服务实例
ai_service = AIService()