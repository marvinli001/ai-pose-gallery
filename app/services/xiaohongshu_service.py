"""
小红书数据源服务
"""
import asyncio
import httpx
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urljoin, urlparse

from app.config import get_settings
from app.services.gpt4o_service import gpt4o_analyzer

settings = get_settings()


class XiaohongshuService:
    """小红书数据获取服务"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # 小红书搜索关键词库
        self.search_keywords = [
            "姿势参考", "pose参考", "人物姿势", "拍照姿势",
            "摄影姿势", "模特姿势", "写真姿势", "人像摄影",
            "坐姿参考", "站姿参考", "躺姿参考", "动作参考",
            "商务照姿势", "休闲照姿势", "职业照姿势",
            "艺术照姿势", "生活照姿势", "街拍姿势"
        ]
    
    async def search_pose_references(self, keyword: str, limit: int = 20) -> Dict[str, Any]:
        """搜索小红书姿势参考内容"""
        try:
            print(f"🔍 搜索小红书内容: {keyword}")
            
            # 模拟搜索API调用（实际需要真实的小红书API或爬虫）
            search_results = await self._simulate_search(keyword, limit)
            
            # 使用GPT-4o分析和过滤内容
            filtered_results = await self._filter_and_analyze_content(search_results, keyword)
            
            return {
                "success": True,
                "keyword": keyword,
                "total_found": len(search_results),
                "filtered_count": len(filtered_results),
                "results": filtered_results,
                "source": "xiaohongshu"
            }
            
        except Exception as e:
            print(f"❌ 小红书搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "keyword": keyword,
                "results": []
            }
    
    async def _simulate_search(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """模拟小红书搜索结果（实际项目中需要替换为真实API）"""
        # 这里模拟返回小红书搜索结果
        # 在实际项目中，你需要：
        # 1. 申请小红书开放平台API
        # 2. 或者使用合规的爬虫方案
        # 3. 或者使用第三方数据服务
        
        mock_results = []
        for i in range(min(limit, 10)):
            mock_results.append({
                "id": f"xhs_{hashlib.md5(f'{keyword}_{i}'.encode()).hexdigest()[:12]}",
                "title": f"{keyword}教程第{i+1}期 - 小红书用户",
                "description": f"分享{keyword}的实用技巧，包含多种{keyword}示例，适合新手学习参考。",
                "author": f"用户{i+1:03d}",
                "images": [
                    f"https://example.com/xhs_image_{i}_{j}.jpg" for j in range(3)
                ],
                "tags": [keyword, "姿势", "参考", "教程"],
                "like_count": 100 + i * 50,
                "comment_count": 20 + i * 5,
                "share_count": 10 + i * 2,
                "publish_time": (datetime.now() - timedelta(days=i)).isoformat(),
                "url": f"https://www.xiaohongshu.com/explore/{hashlib.md5(f'{keyword}_{i}'.encode()).hexdigest()}",
                "category": "lifestyle"
            })
        
        # 模拟网络延迟
        await asyncio.sleep(0.5)
        
        return mock_results
    
    async def _filter_and_analyze_content(self, results: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """使用GPT-4o分析和过滤小红书内容"""
        if not results:
            return []
        
        try:
            # 构建分析提示词
            content_summary = []
            for i, result in enumerate(results[:10]):  # 限制分析数量
                content_summary.append(f"{i+1}. 标题: {result['title']}\n   描述: {result['description']}\n   标签: {', '.join(result['tags'])}")
            
            analysis_prompt = f"""作为内容分析专家，请分析这些小红书搜索结果，判断哪些内容真正适合作为"{keyword}"的参考资料。

搜索关键词：{keyword}

内容列表：
{chr(10).join(content_summary)}

请分析每个内容的相关性，并返回JSON格式：
{{
    "analysis": "整体分析结果",
    "relevant_items": [
        {{
            "index": 1,
            "relevance_score": 0.9,
            "reason": "相关性原因",
            "suggested_tags": ["建议的标签"],
            "quality_score": 0.8
        }}
    ],
    "filtering_summary": "过滤总结"
}}"""

            # 调用GPT-4o进行内容分析
            analysis_result = await gpt4o_analyzer._call_gpt4o_text_api(analysis_prompt)
            
            try:
                analysis_data = json.loads(analysis_result)
                relevant_items = analysis_data.get("relevant_items", [])
                
                # 根据分析结果过滤内容
                filtered_results = []
                for item in relevant_items:
                    index = item.get("index", 1) - 1
                    if 0 <= index < len(results) and item.get("relevance_score", 0) >= 0.6:
                        result = results[index].copy()
                        result.update({
                            "ai_relevance_score": item.get("relevance_score", 0),
                            "ai_quality_score": item.get("quality_score", 0),
                            "ai_analysis_reason": item.get("reason", ""),
                            "ai_suggested_tags": item.get("suggested_tags", []),
                            "filtered_by": "gpt-4o"
                        })
                        filtered_results.append(result)
                
                return filtered_results
                
            except json.JSONDecodeError:
                print("❌ GPT-4o返回结果解析失败，使用基础过滤")
                return await self._basic_filter(results, keyword)
                
        except Exception as e:
            print(f"❌ GPT-4o内容分析失败: {e}")
            return await self._basic_filter(results, keyword)
    
    async def _basic_filter(self, results: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """基础内容过滤（不依赖GPT-4o）"""
        filtered = []
        
        for result in results:
            # 基于关键词和互动数据的简单过滤
            title_score = self._calculate_keyword_score(result.get("title", ""), keyword)
            desc_score = self._calculate_keyword_score(result.get("description", ""), keyword)
            
            # 基于点赞数的质量评分
            like_count = result.get("like_count", 0)
            quality_score = min(like_count / 1000, 1.0)  # 归一化到0-1
            
            total_score = (title_score + desc_score) / 2 + quality_score * 0.3
            
            if total_score >= 0.5:
                result.update({
                    "ai_relevance_score": total_score,
                    "ai_quality_score": quality_score,
                    "ai_analysis_reason": "基于关键词和互动数据的基础评分",
                    "ai_suggested_tags": [keyword],
                    "filtered_by": "basic"
                })
                filtered.append(result)
        
        return filtered
    
    def _calculate_keyword_score(self, text: str, keyword: str) -> float:
        """计算文本与关键词的相关性得分"""
        if not text or not keyword:
            return 0.0
        
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # 精确匹配
        if keyword_lower in text_lower:
            return 1.0
        
        # 部分匹配
        keyword_chars = set(keyword_lower)
        text_chars = set(text_lower)
        overlap = len(keyword_chars & text_chars)
        
        return overlap / len(keyword_chars) if keyword_chars else 0.0
    
    async def download_and_analyze_image(self, image_url: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """下载小红书图片并进行GPT-4o分析"""
        try:
            # 下载图片
            response = await self.client.get(image_url)
            if response.status_code != 200:
                raise Exception(f"图片下载失败: {response.status_code}")
            
            image_content = response.content
            
            # 临时保存图片用于分析
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(image_content)
                temp_path = temp_file.name
            
            try:
                # 使用GPT-4o分析图片
                analysis_result = await gpt4o_analyzer.analyze_for_search(temp_path)
                
                if analysis_result.get("success"):
                    analysis = analysis_result["analysis"]
                    
                    return {
                        "success": True,
                        "image_url": image_url,
                        "file_size": len(image_content),
                        "analysis": analysis,
                        "context": context,
                        "source": "xiaohongshu"
                    }
                else:
                    raise Exception("GPT-4o分析失败")
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            print(f"❌ 小红书图片分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_url": image_url
            }
    
    async def batch_import_content(self, keywords: List[str], limit_per_keyword: int = 10) -> Dict[str, Any]:
        """批量导入小红书内容"""
        print(f"🔄 开始批量导入小红书内容，关键词: {keywords}")
        
        all_results = []
        import_stats = {
            "total_searched": 0,
            "total_found": 0,
            "total_filtered": 0,
            "success_count": 0,
            "error_count": 0,
            "keywords_processed": []
        }
        
        for keyword in keywords:
            try:
                print(f"🔍 处理关键词: {keyword}")
                
                # 搜索内容
                search_result = await self.search_pose_references(keyword, limit_per_keyword)
                
                if search_result.get("success"):
                    results = search_result.get("results", [])
                    
                    # 更新统计
                    import_stats["total_searched"] += 1
                    import_stats["total_found"] += search_result.get("total_found", 0)
                    import_stats["total_filtered"] += search_result.get("filtered_count", 0)
                    import_stats["success_count"] += len(results)
                    import_stats["keywords_processed"].append(keyword)
                    
                    # 添加到结果列表
                    for result in results:
                        result["source_keyword"] = keyword
                        all_results.append(result)
                else:
                    import_stats["error_count"] += 1
                    print(f"❌ 关键词 {keyword} 搜索失败")
                
                # 避免请求过于频繁
                await asyncio.sleep(1)
                
            except Exception as e:
                import_stats["error_count"] += 1
                print(f"❌ 处理关键词 {keyword} 时出错: {e}")
        
        return {
            "success": True,
            "results": all_results,
            "stats": import_stats,
            "message": f"批量导入完成，共处理 {len(keywords)} 个关键词，获得 {len(all_results)} 个结果"
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 创建全局小红书服务实例
xiaohongshu_service = XiaohongshuService()