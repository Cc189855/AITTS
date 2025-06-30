import requests
import json
import os
import time
from datetime import datetime
import base64
import re
import hashlib
import sys
import logging

# 配置文件路径
CONFIG_FILE = "Fish_tts_config.json"

# API基础URL
API_BASE_URL = "https://pkc-proxy.98tt.me/v1"

# 默认配置
DEFAULT_CONFIG = {
    "api_key": "",
    "voices": {
        "default": {
            "voice_id": "default",
            "backend": "speech-1.6",
            "format": "mp3",
            "temperature": 0.7,
            "top_p": 0.7,
            "chunk_length": 200,
            "normalize": True,
            "prosody_volume": 0.0
        }
    },
    "output_paths": {
        "default": "/storage/emulated/0/Download/output"
    },
    "format_options": ["mp3", "wav", "ogg", "flac", "pcm"],
    "backend_options": ["speech-1.6", "speech-1.5", "s1"],
    "history": [],
    "last_used": {
        "voice": "default",
        "output": "default"
    }
}

class TTSManager:
    def __init__(self):
        self.config = self.load_config()
        # 确保"last_used"字典中有"output"键
        self.current_voice = self.config["last_used"].get("voice", "default")
        self.current_output_path = self.config["last_used"].get("output", "default")
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    # 添加缺失字段
                    config.setdefault("output_paths", DEFAULT_CONFIG["output_paths"].copy())
                    config.setdefault("format_options", DEFAULT_CONFIG["format_options"].copy())
                    config.setdefault("backend_options", DEFAULT_CONFIG["backend_options"].copy())
                    config.setdefault("history", [])
                    config.setdefault("last_used", DEFAULT_CONFIG["last_used"].copy())
                    
                    # 确保"last_used"字典中有"voice"和"output"键
                    config["last_used"].setdefault("voice", "default")
                    config["last_used"].setdefault("output", "default")
                    
                    # 确保每个声音配置都有voice_id字段
                    for name, profile in config["voices"].items():
                        profile.setdefault("voice_id", "default")
                    
                    return config
            except:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """保存配置文件"""
        # 更新最后使用配置
        self.config["last_used"] = {
            "voice": self.current_voice,
            "output": self.current_output_path
        }
        
        # 确保输出目录存在
        for path in self.config["output_paths"].values():
            os.makedirs(path, exist_ok=True)
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def get_headers(self):
        """获取API请求头"""
        return {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json",
            "User-Agent": "FishAudioTTS/2.0"
        }
    
    def set_api_key(self, key):
        """设置API密钥"""
        self.config["api_key"] = key
        self.save_config()
        return "🔑 API密钥已保存！"
    
    def create_voice_profile(self, name, voice_id="default", backend="speech-1.6", format="mp3", temperature=0.7, 
                            top_p=0.7, chunk_length=200, normalize=True, 
                            prosody_volume=0.0):
        """创建自定义声音配置"""
        # 检查名称是否已存在
        if name in self.config["voices"]:
            return "⚠️ 配置名称已存在！"
        
        self.config["voices"][name] = {
            "voice_id": voice_id,
            "backend": backend,
            "format": format,
            "temperature": temperature,
            "top_p": top_p,
            "chunk_length": chunk_length,
            "normalize": normalize,
            "prosody_volume": prosody_volume
        }
        self.save_config()
        return f"🎶 声音配置 '{name}' 已创建！"
    
    def edit_voice_profile(self, name, voice_id=None, backend=None, format=None, temperature=None, 
                          top_p=None, chunk_length=None, normalize=None, 
                          prosody_volume=None):
        """编辑现有声音配置"""
        if name not in self.config["voices"]:
            return "⚠️ 配置不存在"
        
        profile = self.config["voices"][name]
        if voice_id: profile["voice_id"] = voice_id
        if backend: profile["backend"] = backend
        if format: profile["format"] = format
        if temperature: profile["temperature"] = temperature
        if top_p: profile["top_p"] = top_p
        if chunk_length: profile["chunk_length"] = chunk_length
        if normalize is not None: profile["normalize"] = normalize
        if prosody_volume: profile["prosody_volume"] = prosody_volume
        
        self.save_config()
        return f"🎛️ 声音配置 '{name}' 已更新！"
    
    def delete_voice_profile(self, name):
        """删除声音配置"""
        if name == "default":
            return "❌ 不能删除默认配置"
            
        if name in self.config["voices"]:
            del self.config["voices"][name]
            # 如果删除的是当前配置，重置为默认
            if self.current_voice == name:
                self.current_voice = "default"
            self.save_config()
            return f"🗑️ 声音配置 '{name}' 已删除！"
        return "⚠️ 配置不存在"
    
    def add_output_path(self, name, path):
        """添加输出路径配置"""
        if name in self.config["output_paths"]:
            return "⚠️ 路径名称已存在"
        
        # 创建目录
        os.makedirs(path, exist_ok=True)
        self.config["output_paths"][name] = path
        self.save_config()
        return f"📁 输出路径 '{name}' 已添加"
    
    def clear_history(self):
        """清空历史记录"""
        self.config["history"] = []
        self.save_config()
        return "✅ 历史记录已清空！"
    
    def select_from_menu(self, title, options, current_value=None):
        """显示选择菜单并获取用户选择"""
        print(f"\n\033[1;36m{title}:\033[0m")
        for i, option in enumerate(options, 1):
            indicator = " (当前)" if current_value == option else ""
            print(f"{i}. {option}{indicator}")
        
        choice = input("\n请选择: ")
        if choice.strip() == "":
            return current_value
            
        try:
            index = int(choice) - 1
            if 0 <= index < len(options):
                return options[index]
        except:
            pass
        return current_value if current_value else options[0]

    def format_filename(self, text, format):
        """根据文本生成文件名（去掉voice_id前缀）"""
        # 提取前20个字符作为文件名
        clean_text = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', text[:20])
        if not clean_text:
            clean_text = "tts_audio"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{clean_text}_{timestamp}.{format}"

    def test_api_connection(self):
        """测试API连接状态"""
        print("\n测试API连接...")
        try:
            response = requests.head(
                f"{API_BASE_URL}/voices",
                headers=self.get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True
            else:
                print(f"❌ API响应异常 (状态码 {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ 无法连接到API: {str(e)}")
            return False

    def text_to_speech(self, text, voice_profile_name=None, speed=1.0):
        """文字转语音 - 使用最新API规范"""
        # 如果没有指定声音配置，使用当前配置
        if voice_profile_name is None:
            voice_profile = self.config["voices"].get(self.current_voice, {})
            profile_name = self.current_voice
        else:
            voice_profile = self.config["voices"].get(voice_profile_name, {})
            profile_name = voice_profile_name
        
        if not voice_profile:
            return "❌ 未找到声音配置"
        
        try:
            # 根据文档构造请求体
            payload = {
                "text": text,
                "reference_id": voice_profile["voice_id"],
                "backend": voice_profile["backend"],
                "format": voice_profile["format"],
                "temperature": voice_profile["temperature"],
                "top_p": voice_profile["top_p"],
                "chunk_length": voice_profile["chunk_length"],
                "normalize": voice_profile["normalize"],
                "speed": speed,
                "volume": voice_profile["prosody_volume"]
            }
            
            # 发送请求到新的端点
            response = requests.post(
                f"{API_BASE_URL}/tts",
                json=payload,
                headers=self.get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                # 尝试解析JSON响应
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    # 不是JSON响应 - 可能是音频二进制数据
                    audio_data = response.content
                    # 检查音频文件签名
                    if audio_data.startswith(b'RIFF') or audio_data.startswith(b'\xFF\xFB'):
                        data = {"audio": base64.b64encode(audio_data).decode('utf-8')}
                    else:
                        # 可能是错误消息
                        return f"❌ 无效响应: {response.text[:200]}"
                
                # 获取音频数据
                if "audio" in data:
                    audio_content = data["audio"]
                else:
                    return "❌ 响应中未包含音频数据"
                    
                # 获取输出路径
                output_dir = self.config["output_paths"].get(self.current_output_path, "./")
                # 使用新的文件名格式（去掉voice_id）
                filename = os.path.join(
                    output_dir, 
                    self.format_filename(text, voice_profile["format"])
                )
                
                # 保存音频文件（Base64解码）
                try:
                    audio_data = base64.b64decode(audio_content)
                except base64.binascii.Error:
                    # 如果已经是原始二进制数据
                    audio_data = audio_content
                
                with open(filename, "wb") as f:
                    f.write(audio_data)
                
                # 保存历史记录 - 使用配置名称而不是声音ID
                self.config["history"].insert(0, {
                    "text": text,
                    "voice_profile": profile_name,  # 使用配置名称
                    "backend": voice_profile["backend"],
                    "timestamp": datetime.now().isoformat(),
                    "filename": filename,
                    "speed": speed
                })
                # 只保留最近的20条记录
                self.config["history"] = self.config["history"][:20]
                self.save_config()
                
                return f"🔊 语音生成成功！保存为: {filename}"
            else:
                # 处理非200响应
                try:
                    error_msg = response.json().get("error", {})
                except json.JSONDecodeError:
                    error_msg = f"非JSON响应: {response.text[:200]}"
                
                return f"❌ 请求失败 (状态码 {response.status_code}): {error_msg}"
        except Exception as e:
            # 捕获所有异常
            return f"❌ 发生错误: {str(e)}"

def print_menu():
    """打印菜单 - 优化样式"""
    menu_width = 40
    separator = "=" * menu_width
    
    print(f"\n\033[1;36m{separator}\033[0m")
    print("\033[1;35m AI真人语音生成高级版 \033[0m".center(menu_width))
    print(f"\033[1;36m{separator}\033[0m")
    
    menu_items = [
        "1. 真人语音生成 🎧 ",
        "2. 管理声音配置 ⚙️ ",
        "3. 设置API密钥 🔑 ",
        "4. 查看历史记录 📜 ",
        "5. 管理输出路径 📁 ",
        "6. 测试API连接 📶 ",
        "7. 退出 🚪 "
    ]
    
    for item in menu_items:
        print(f"\033[1;37m{item}\033[0m")
    
    print(f"\033[1;36m{separator}\033[0m")

def manage_voice_profiles(manager):
    """管理声音配置界面"""
    while True:
        menu_width = 40
        separator = "=" * menu_width
        
        print(f"\n\033[1;33m{separator}\033[0m")
        print("\033[1;33m 声音配置管理 \033[0m".center(menu_width))
        print(f"\033[1;33m{separator}\033[0m")
        
        menu_items = [
            "1. 列出所有配置",
            "2. 创建新配置",
            "3. 编辑配置",
            "4. 删除配置",
            "5. 切换当前配置",
            "6. 返回主菜单"
        ]
        
        for item in menu_items:
            print(f"\033[1;37m{item}\033[0m")
        
        print(f"\033[1;33m{separator}\033[0m")
        
        choice = input("\n请选择操作: ")
        
        if choice == "1":
            print("\n当前声音配置:")
            for name, profile in manager.config["voices"].items():
                is_current = " (当前使用)" if manager.current_voice == name else ""
                print(f"- {name}{is_current}:")
                print(f"  声音ID: {profile['voice_id']}")
                print(f"  后端: {profile['backend']}")
                print(f"  格式: {profile['format']}")
                print(f"  温度: {profile['temperature']}")
                print(f"  Top-p: {profile['top_p']}")
                print(f"  分块长度: {profile['chunk_length']}")
                print(f"  标准化: {'是' if profile['normalize'] else '否'}")
                print(f"  音量: {profile['prosody_volume']}")
        
        elif choice == "2":
            name = input("\n输入新配置名称: ")
            if name in manager.config["voices"]:
                print("⚠️ 配置名称已存在！")
                continue
                
            # 首先获取声音ID
            voice_id = input("输入声音ID (如'default'): ").strip()
            if not voice_id:
                print("❌ 声音ID不能为空")
                continue
                
            # 后端模型选择
            backend = manager.select_from_menu(
                "后端模型",
                manager.config["backend_options"],
                "speech-1.6"
            )
            
            # 音频格式选择
            format = manager.select_from_menu(
                "音频格式",
                manager.config["format_options"],
                "mp3"
            )
            
            temperature = float(input("温度 (0.0-1.0, 默认0.7): ") or "0.7")
            top_p = float(input("Top-p (0.0-1.0, 默认0.7): ") or "0.7")
            chunk_length = int(input("分块长度 (默认200): ") or "200")
            normalize = input("标准化 (y/n, 默认y): ").lower() in ['y', 'yes', '']
            prosody_volume = float(input("音量 (-1.0-1.0, 默认0.0): ") or "0.0")
            
            print(manager.create_voice_profile(
                name, voice_id, backend, format, temperature, top_p, 
                chunk_length, normalize, prosody_volume
            ))
        
        elif choice == "3":
            print("\n可用配置:")
            voices = list(manager.config["voices"].keys())
            for i, name in enumerate(voices, 1):
                is_current = " (当前)" if manager.current_voice == name else ""
                print(f"{i}. {name}{is_current}")
            choice_idx = int(input("\n选择要编辑的配置编号: ")) - 1
            name = voices[choice_idx]
            profile = manager.config["voices"][name]
            
            print(f"\n编辑配置: {name}")
            print(f"当前声音ID: {profile['voice_id']}")
            print(f"当前后端: {profile['backend']}")
            print(f"当前格式: {profile['format']}")
            print(f"当前温度: {profile['temperature']}")
            print(f"当前Top-p: {profile['top_p']}")
            print(f"当前分块长度: {profile['chunk_length']}")
            print(f"当前标准化: {'是' if profile['normalize'] else '否'}")
            print(f"当前音量: {profile['prosody_volume']}")
            
            new_voice_id = input(f"新声音ID（回车保持当前）: ") or profile['voice_id']
            
            # 后端模型选择
            new_backend = manager.select_from_menu(
                "新后端",
                manager.config["backend_options"],
                profile['backend']
            )
            
            # 音频格式选择
            new_format = manager.select_from_menu(
                "新格式",
                manager.config["format_options"],
                profile['format']
            )
            
            new_temperature = float(input(f"新温度（回车保持当前）: ") or profile['temperature'])
            new_top_p = float(input(f"新Top-p（回车保持当前）: ") or profile['top_p'])
            new_chunk_length = int(input(f"新分块长度（回车保持当前）: ") or profile['chunk_length'])
            new_normalize = input(f"新标准化 (y/n, 默认{profile['normalize']}): ").lower()
            new_normalize = profile['normalize'] if new_normalize == "" else new_normalize in ['y', 'yes']
            new_prosody_volume = float(input(f"新音量（回车保持当前）: ") or profile['prosody_volume'])
            
            print(manager.edit_voice_profile(
                name, new_voice_id, new_backend, new_format, new_temperature, 
                new_top_p, new_chunk_length, new_normalize, 
                new_prosody_volume
            ))
        
        elif choice == "4":
            print("\n可用配置:")
            voices = list(manager.config["voices"].keys())
            for i, name in enumerate(voices, 1):
                print(f"{i}. {name}")
            choice_idx = int(input("\n选择要删除的配置编号: ")) - 1
            name = voices[choice_idx]
            
            if name == "default":
                print("❌ 不能删除默认配置！")
                continue
                
            confirm = input(f"确定要删除 '{name}' 配置吗? (y/n): ").lower()
            if confirm == "y":
                print(manager.delete_voice_profile(name))
        
        elif choice == "5":
            print("\n可用配置:")
            voices = list(manager.config["voices"].keys())
            for i, name in enumerate(voices, 1):
                is_current = " (当前)" if manager.current_voice == name else ""
                print(f"{i}. {name}{is_current}")
            choice_idx = int(input("\n选择配置编号: ")) - 1
            manager.current_voice = voices[choice_idx]
            print(f"\n✅ 当前配置已切换为: {manager.current_voice}")
        
        elif choice == "6":
            break
        
        time.sleep(1)

def manage_output_paths(manager):
    """管理输出路径配置"""
    while True:
        menu_width = 40
        separator = "=" * menu_width
        
        print(f"\n\033[1;34m{separator}\033[0m")
        print("\033[1;34m 输出路径管理 \033[0m".center(menu_width))
        print(f"\033[1;34m{separator}\033[0m")
        
        menu_items = [
            "1. 列出所有路径",
            "2. 添加新路径",
            "3. 删除路径",
            "4. 切换当前路径",
            "5. 返回主菜单"
        ]
        
        for item in menu_items:
            print(f"\033[1;37m{item}\033[0m")
        
        print(f"\033[1;34m{separator}\033[0m")
        
        choice = input("\n请选择操作: ")
        
        if choice == "1":
            print("\n当前输出路径:")
            for name, path in manager.config["output_paths"].items():
                is_current = " (当前使用)" if manager.current_output_path == name else ""
                print(f"- {name}{is_current}: {path}")
        
        elif choice == "2":
            name = input("\n输入路径名称: ")
            path = input("输入完整路径: ").strip()
            
            if not os.path.exists(path):
                create = input("目录不存在，是否创建? (y/n): ").lower()
                if create != "y":
                    continue
                os.makedirs(path, exist_ok=True)
            
            print(manager.add_output_path(name, path))
        
        elif choice == "3":
            paths = list(manager.config["output_paths"].keys())
            if len(paths) <= 1:
                print("❌ 至少需要保留一个输出路径！")
                continue
                
            print("\n可用路径:")
            for i, name in enumerate(paths, 1):
                print(f"{i}. {name}")
            choice_idx = int(input("\n选择要删除的路径编号: ")) - 1
            name = paths[choice_idx]
            
            if name == "default":
                print("❌ 不能删除默认路径！")
                continue
                
            confirm = input(f"确定要删除 '{name}' 路径吗? (y/n): ").lower()
            if confirm == "y":
                del manager.config["output_paths"][name]
                # 如果删除的是当前路径，切换到默认
                if manager.current_output_path == name:
                    manager.current_output_path = "default"
                print(f"🗑️ 输出路径 '{name}' 已删除！")
                manager.save_config()
        
        elif choice == "4":
            print("\n可用路径:")
            paths = list(manager.config["output_paths"].keys())
            for i, name in enumerate(paths, 1):
                is_current = " (当前)" if manager.current_output_path == name else ""
                print(f"{i}. {name}{is_current}")
            choice_idx = int(input("\n选择路径编号: ")) - 1
            manager.current_output_path = paths[choice_idx]
            print(f"\n✅ 当前输出路径已切换为: {manager.current_output_path}")
        
        elif choice == "5":
            break
        
        time.sleep(1)

def main():
    # 设置基本的日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    manager = TTSManager()
    
    # 确保输出目录存在
    for path in manager.config["output_paths"].values():
        os.makedirs(path, exist_ok=True)
    
    while True:
        print_menu()
        choice = input("\n请选择操作: ")
        
        if choice == "1":
            text = input("\n请输入要转换的文本: ")
            
            # 输入语速
            while True:
                try:
                    speed = float(input("请输入语速 (0.5-2.0, 默认1.0): ") or "1.0")
                    if 0.5 <= speed <= 2.0:
                        break
                    else:
                        print("❌ 语速必须在0.5到2.0之间")
                except ValueError:
                    print("❌ 请输入有效的数字")
            
            # 列出所有声音配置
            print("\n\033[1;32m可用声音配置:\033[0m")
            voices = list(manager.config["voices"].keys())
            for i, name in enumerate(voices, 1):
                is_current = " (当前)" if manager.current_voice == name else ""
                print(f"{i}. {name}{is_current}")
            
            # 选择配置
            selected_config = manager.current_voice
            try:
                choice_input = input("请选择配置序号(回车使用当前): ")
                if choice_input.strip():
                    choice_idx = int(choice_input) - 1
                    if 0 <= choice_idx < len(voices):
                        selected_config = voices[choice_idx]
                    else:
                        print("❌ 选择无效，使用当前配置")
            except ValueError:
                print("❌ 输入无效，使用当前配置")
            
            # 列出所有输出路径
            print("\n\033[1;32m可用输出路径:\033[0m")
            paths = list(manager.config["output_paths"].keys())
            for i, name in enumerate(paths, 1):
                is_current = " (当前)" if manager.current_output_path == name else ""
                print(f"{i}. {name}{is_current}")
            
            # 选择路径
            try:
                choice_input = input("请选择输出路径序号(回车使用当前): ")
                if choice_input.strip():
                    choice_idx = int(choice_input) - 1
                    if 0 <= choice_idx < len(paths):
                        manager.current_output_path = paths[choice_idx]
            except ValueError:
                print("❌ 输入无效，使用当前路径")
            
            print("\n生成中...")
            result = manager.text_to_speech(text, selected_config, speed)
            print(f"\n{result}")
        
        elif choice == "2":
            manage_voice_profiles(manager)
        
        elif choice == "3":
            key = input("\n请输入API密钥: ")
            print(manager.set_api_key(key))
        
        elif choice == "4":
            print("\n历史记录:")
            if not manager.config["history"]:
                print("暂无历史记录")
            else:
                for i, record in enumerate(manager.config["history"], 1):
                    print(f"{i}. [{record['timestamp'][:19]}]")
                    # 使用配置名称而不是声音ID
                    print(f"   配置: {record['voice_profile']}")
                    print(f"   后端: {record['backend']}")
                    print(f"   语速: {record['speed']}")
                    print(f"   文件: {record['filename']}")
                    print("-" * 40)
            
            if manager.config["history"]:
                print("\n操作选项:")
                print("1. 清空历史记录")
                print("2. 返回主菜单")
                
                action = input("\n请选择操作: ")
                
                if action == "1":
                    confirm = input("\n确定要清空所有历史记录吗? (y/n): ").lower()
                    if confirm == "y":
                        print(manager.clear_history())
                elif action == "2":
                    continue
                else:
                    print("❌ 请选择有效的选项")
            else:
                input("\n按回车键返回主菜单...")
        
        elif choice == "5":
            manage_output_paths(manager)
        
        elif choice == "6":
            if manager.test_api_connection():
                print("✅ API连接正常")
            else:
                print("❌ 无法连接到API，请检查API密钥和网络连接")
        
        elif choice == "7":
            print("\n感谢使用，再见！")
            break
        
        else:
            print("❌ 请选择有效的选项")
        
        time.sleep(1)

if __name__ == "__main__":
    main()
