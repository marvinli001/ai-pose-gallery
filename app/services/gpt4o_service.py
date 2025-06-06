"""
GPT-4o 图像分析服务
"""
import base64
import httpx
import json
import asyncio
from typing import List, Dict, Any, Optional
from PIL import Image
import io
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class GPT4oImageAnalyzer:
    """GPT-4o 图像分析器"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.image_analysis_timeout)
        self.model = settings.openai_model
        
    async def analyze_image_comprehensive(self, image_path: str, user_query: str = None) -> Dict[str, Any]:
        """
        使用GPT-4o进行全面的图像分析
        支持自定义查询需求
        """
        try:
            # 准备图像数据
            image_data = await self._prepare_image_for_gpt4o(image_path)
            
            # 构建分析提示词
            prompt = self._build_analysis_prompt(user_query)
            
            # 调用GPT-4o API
            result = await self._call_gpt4o_vision_api(image_data, prompt)
            
            # 解析和验证结果
            parsed_result = await self._parse_and_validate_result(result)
            
            return {
                "success": True,
                "analysis": parsed_result,
                "model": self.model,
                "image_path": image_path
            }
            
        except Exception as e:
            print(f"❌ GPT-4o分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_analysis": await self._get_fallback_analysis(image_path)
            }
    
    async def analyze_for_search(self, image_path: str) -> Dict[str, Any]:
        """专门为搜索优化的图像分析"""
        search_prompt = """请作为专业的图像标注专家，详细分析这张图片，重点关注以下方面：

1. **人物特征**：
   - 性别、年龄段
   - 表情和情绪状态
   - 发型、服装风格

2. **姿势和动作**：
   - 身体姿态（站、坐、躺、蹲等）
   - 手势和肢体动作
   - 视线方向和角度

3. **场景环境**：
   - 室内/户外
   - 具体场所类型
   - 背景元素

4. **拍摄特征**：
   - 拍摄角度（正面、侧面、背面等）
   - 光线条件
   - 构图风格

5. **道具和物品**：
   - 明显的道具或物品
   - 服装配饰
   - 环境物品

请以JSON格式返回分析结果，包含：
{
    "description": "详细的图片描述（100-200字）",
    "tags": {
        "pose": ["具体姿势标签"],
        "gender": ["性别"],
        "age": ["年龄段"],
        "clothing": ["服装风格"],
        "scene": ["场景类型"],
        "lighting": ["光线类型"],
        "angle": ["拍摄角度"],
        "emotion": ["表情情绪"],
        "action": ["动作行为"],
        "props": ["道具物品"]
    },
    "searchable_keywords": ["适合搜索的关键词列表"],
    "mood": "整体氛围描述",
    "style": "视觉风格描述",
    "confidence": 0.95
}

确保标签准确、具体，便于后续搜索匹配。"""

        return await self.analyze_image_comprehensive(image_path, search_prompt)
    
    async def search_similar_images(self, query: str, image_descriptions: List[str]) -> Dict[str, Any]:
        """使用GPT-4o进行语义相似度匹配"""
        prompt = f"""作为图片搜索专家，请分析用户查询和图片描述的相似度。

用户查询："{query}"

请对以下图片描述进行相似度评分（0-1分）并排序：

{chr(10).join([f"{i+1}. {desc}" for i, desc in enumerate(image_descriptions)])}

请返回JSON格式：
{{
    "query_analysis": "查询意图分析",
    "matches": [
        {{
            "index": 1,
            "similarity_score": 0.95,
            "reasoning": "匹配原因"
        }}
    ]
}}"""

        try:
            response = await self._call_gpt4o_text_api(prompt)
            return json.loads(response)
        except Exception as e:
            print(f"❌ 语义搜索失败: {e}")
            return {"matches": []}
    
    async def enhance_search_query(self, user_query: str) -> Dict[str, Any]:
        """增强和扩展用户搜索查询"""
        prompt = f"""作为搜索查询优化专家，请分析并扩展用户的搜索查询。

用户查询："{user_query}"

请提供：
1. 查询意图分析
2. 关键词提取和同义词扩展
3. 可能的相关搜索建议
4. 搜索标签分类

返回JSON格式：
{{
    "original_query": "{user_query}",
    "intent": "查询意图",
    "keywords": ["关键词列表"],
    "synonyms": ["同义词扩展"],
    "related_searches": ["相关搜索建议"],
    "tag_categories": {{
        "pose": ["姿势相关"],
        "scene": ["场景相关"],
        "style": ["风格相关"]
    }},
    "enhanced_query": "优化后的查询"
}}"""

        try:
            response = await self._call_gpt4o_text_api(prompt)
            return json.loads(response)
        except Exception as e:
            print(f"❌ 查询增强失败: {e}")
            return {"enhanced_query": user_query}
    
    async def _prepare_image_for_gpt4o(self, image_path: str) -> str:
        """为GPT-4o准备图像数据"""
        try:
            with Image.open(image_path) as img:
                # 转换为RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 优化尺寸 - GPT-4o支持更大的图片
                max_size = 2048  # GPT-4o支持更高分辨率
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # 转换为base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=90, optimize=True)
                image_bytes = buffer.getvalue()
                
                return base64.b64encode(image_bytes).decode('utf-8')
                
        except Exception as e:
            print(f"❌ 图片预处理失败: {e}")
            raise
    
    def _build_analysis_prompt(self, custom_query: str = None) -> str:
        """构建分析提示词"""
        if custom_query:
            return custom_query
        
        return """请作为专业的图像分析AI，全面分析这张图片的内容。重点关注：

1. 人物特征（性别、年龄、表情、服装）
2. 姿势和动作（站、坐、躺、手势等）
3. 场景环境（室内/户外、具体场所）
4. 拍摄角度和构图
5. 光线和氛围
6. 可见的物品和道具

请提供详细、准确的描述，并生成便于搜索的标签。以JSON格式返回结果。"""
    
    async def _call_gpt4o_vision_api(self, image_data: str, prompt: str) -> str:
        """调用GPT-4o Vision API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"  # 使用高质量分析
                            }
                        }
                    ]
                }
            ],
            "max_tokens": settings.openai_max_tokens,
            "temperature": settings.openai_temperature
        }
        
        response = await self.client.post(
            f"{settings.openai_base_url}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"OpenAI API错误: {response.status_code} - {response.text}")
    
    async def _call_gpt4o_text_api(self, prompt: str) -> str:
        """调用GPT-4o Text API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": settings.openai_max_tokens,
            "temperature": settings.openai_temperature
        }
        
        response = await self.client.post(
            f"{settings.openai_base_url}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"OpenAI API错误: {response.status_code} - {response.text}")
    
    async def _parse_and_validate_result(self, result: str) -> Dict[str, Any]:
        """解析和验证GPT-4o返回结果"""
        try:
            # 尝试直接解析JSON
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError:
            # 如果不是JSON，尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    return parsed
                except:
                    pass
            
            # 如果解析失败，返回文本分析结果
            return {
                "description": result,
                "tags": self._extract_tags_from_text(result),
                "confidence": 0.7
            }
    
    def _extract_tags_from_text(self, text: str) -> Dict[str, List[str]]:
        """从文本中提取标签"""
        # 简单的关键词提取逻辑
        tags = {
            "pose": [],
            "gender": [],
            "age": [],
            "clothing": [],
            "scene": [],
            "lighting": [],
            "angle": [],
            "emotion": [],
            "action": [],
            "props": []
        }
        
        # 可以根据需要实现更复杂的文本分析
        return tags
    
    async def _get_fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """获取备用分析结果"""
        filename = Path(image_path).name.lower()
        
        return {
            "description": f"图片文件: {filename}",
            "tags": {
                "general": ["图片", "参考"]
            },
            "confidence": 0.3
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 创建全局GPT-4o服务实例
gpt4o_analyzer = GPT4oImageAnalyzer()