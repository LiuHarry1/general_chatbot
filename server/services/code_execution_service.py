"""
代码执行服务
负责执行Python代码并处理结果
"""
import os
import sys
import subprocess
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import asyncio
import json
import base64

from utils.logger import app_logger


class CodeExecutionService:
    """代码执行服务"""
    
    def __init__(self):
        self.images_dir = os.path.join(os.path.dirname(__file__), "..", "images")
        self.ensure_images_dir()
        
        # 预安装的包
        self.required_packages = [
            "matplotlib", "numpy", "pandas", "seaborn", 
            "plotly", "scipy", "sklearn", "requests"
        ]
        
    def ensure_images_dir(self):
        """确保images目录存在"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
            app_logger.info(f"创建图片目录: {self.images_dir}")
    
    async def execute_code(self, code: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        执行Python代码
        
        Args:
            code: 要执行的Python代码
            user_id: 用户ID
            
        Returns:
            执行结果字典
        """
        try:
            app_logger.info(f"开始执行代码，用户: {user_id}")
            app_logger.debug(f"执行代码内容: {code[:200]}...")
            
            # 确保代码是字符串类型且使用UTF-8编码
            if not isinstance(code, str):
                code = str(code)
            
            # 创建临时文件，确保使用UTF-8编码
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # 执行代码
                result = await self._run_code(temp_file, user_id)
                return result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            app_logger.error(f"代码执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "images": []
            }
    
    async def _run_code(self, code_file: str, user_id: str) -> Dict[str, Any]:
        """运行Python代码文件"""
        
        # 构建执行环境
        env = os.environ.copy()
        env['PYTHONPATH'] = ':'.join(sys.path)
        
        # 准备输出目录
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        output_dir = os.path.join(self.images_dir, session_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # 修改代码以支持图片保存
        modified_code = self._prepare_code_for_execution(code_file, output_dir)
        
        # 写入修改后的代码，确保使用UTF-8编码
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(modified_code)
            modified_file = f.name
        
        try:
            # 使用线程池执行器来避免Windows上的asyncio subprocess问题
            import concurrent.futures
            
            def run_python_code():
                """在子进程中运行Python代码"""
                result = subprocess.run(
                    [sys.executable, modified_file],
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=os.path.dirname(modified_file),
                    encoding='utf-8',
                    errors='ignore'
                )
                return result
            
            # 在线程池中执行
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, run_python_code)
            
            # 解码输出
            output = result.stdout
            error_output = result.stderr
            
            # 收集生成的图片
            images = self._collect_generated_images(output_dir)
            
            success = result.returncode == 0
            
            execution_result = {
                "success": success,
                "output": output,
                "error": error_output if not success else "",
                "images": images,
                "session_id": session_id
            }
            
            if success:
                app_logger.info(f"代码执行成功，生成 {len(images)} 个图片")
            else:
                app_logger.error(f"代码执行失败: {error_output}")
                
            return execution_result
            
        finally:
            # 清理临时文件
            if os.path.exists(modified_file):
                os.unlink(modified_file)
    
    def _prepare_code_for_execution(self, code_file: str, output_dir: str) -> str:
        """准备代码执行环境"""
        
        # 尝试多种编码方式读取文件
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']
        original_code = None
        
        for encoding in encodings:
            try:
                with open(code_file, 'r', encoding=encoding) as f:
                    original_code = f.read()
                app_logger.debug(f"成功使用 {encoding} 编码读取文件")
                break
            except UnicodeDecodeError:
                continue
        
        if original_code is None:
            # 如果所有编码都失败，使用错误处理方式读取
            with open(code_file, 'r', encoding='utf-8', errors='replace') as f:
                original_code = f.read()
            app_logger.warning("使用错误处理方式读取文件，可能包含替换字符")
        
        # 添加必要的导入和设置
        prepend_code = f"""
import os
import sys
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 设置输出目录
OUTPUT_DIR = r"{output_dir}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 设置matplotlib中文字体和图片质量
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
# 设置默认图片尺寸和质量 - 进一步优化
plt.rcParams['figure.figsize'] = [6, 4]  # 更小的默认图片尺寸
plt.rcParams['figure.dpi'] = 80  # 进一步降低DPI

# 图片计数器
_image_counter = 0

def save_plot(filename=None):
    \"\"\"保存当前图片\"\"\"
    global _image_counter
    if filename is None:
        filename = f"plot_{{_image_counter}}.png"
        _image_counter += 1
    filepath = os.path.join(OUTPUT_DIR, filename)
    # 使用更低的DPI和压缩设置来进一步减小文件大小
    plt.savefig(filepath, dpi=100, bbox_inches='tight', 
                facecolor='white', edgecolor='none',
                format='png', pad_inches=0.1)
    plt.close()  # 关闭当前图片
    print(f"图片已保存: {{filename}}")
    return filename

# 自动保存所有图片
def show():
    \"\"\"重写show函数，自动保存图片\"\"\"
    save_plot()

# 重写plt.show
plt.show = show

"""
        
        return prepend_code + "\n" + original_code
    
    def _collect_generated_images(self, output_dir: str) -> list:
        """收集生成的图片文件"""
        images = []
        
        if not os.path.exists(output_dir):
            return images
            
        for filename in os.listdir(output_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                # 生成可访问的URL
                relative_path = os.path.relpath(os.path.join(output_dir, filename), self.images_dir)
                image_url = f"/api/v1/images/{relative_path.replace(os.sep, '/')}"
                
                images.append({
                    "filename": filename,
                    "url": image_url,
                    "path": os.path.join(output_dir, filename)
                })
        
        return images
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试简单代码执行
            test_code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)
plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('测试图片')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
save_plot('test_plot.png')
print("测试代码执行成功")
"""
            
            result = await self.execute_code(test_code, "health_check")
            
            return {
                "status": "ok" if result["success"] else "error",
                "message": "代码执行服务正常" if result["success"] else f"代码执行失败: {result['error']}",
                "test_images": len(result["images"])
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"健康检查失败: {str(e)}",
                "test_images": 0
            }


# 创建全局实例
code_execution_service = CodeExecutionService()
