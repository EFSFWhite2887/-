import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import threading
import config
import time
import json

class TimeingManager:
    def __init__(self, root):
        self.root = root
        self.root.title("时间管理系统")
        self.root.geometry("700x500")  # 增大窗口尺寸
        self.root.resizable(True, True)
        
        self.activity_process = None
        self.create_widgets()
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="时间管理系统", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 当前用户信息
        user_frame = ttk.LabelFrame(main_frame, text="当前用户信息")
        user_frame.pack(fill='x', padx=10, pady=10)
        
        user = config.get_active_user()
        ttk.Label(user_frame, text=f"用户名: {user['username']}").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(user_frame, text=f"城市: {user['city']}").grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(user_frame, text=f"Bark Key: {user['bark_key'][:10]}...").grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', padx=10, pady=20)
        
        # 功能按钮
        ttk.Button(button_frame, text="生成时间管理表", command=self.generate_timetable, width=20).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="用户配置管理", command=self.open_config_manager, width=20).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(button_frame, text="刷新用户信息", command=self.refresh_user_info, width=20).grid(row=1, column=0, padx=10, pady=5)
        
        # 活动监控按钮
        self.monitor_button = ttk.Button(button_frame, text="启动活动监控", command=self.toggle_activity_monitor, width=20)
        self.monitor_button.grid(row=1, column=1, padx=10, pady=5)
        
        # 清空日志按钮
        ttk.Button(button_frame, text="清空日志", command=self.clear_log, width=20).grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="系统状态")
        status_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 添加包含滚动条的框架
        text_frame = ttk.Frame(status_frame)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 垂直滚动条
        scrollbar_y = ttk.Scrollbar(text_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 水平滚动条
        scrollbar_x = ttk.Scrollbar(text_frame, orient='horizontal')
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建文本框
        self.status_text = tk.Text(text_frame, wrap=tk.NONE, height=15, width=80,
                                  yscrollcommand=scrollbar_y.set,
                                  xscrollcommand=scrollbar_x.set)
        self.status_text.pack(fill='both', expand=True)
        
        # 设置滚动条与文本框的关联
        scrollbar_y.config(command=self.status_text.yview)
        scrollbar_x.config(command=self.status_text.xview)
        
        # 初始状态
        self.log_status("系统已启动，请选择操作")
    
    def log_status(self, message):
        """添加状态信息到状态显示区域"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        # 确保UI刷新
        self.root.update_idletasks()
    
    def clear_log(self):
        """清空日志信息"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.log_status("日志已清空")
    
    def generate_timetable(self):
        """生成时间管理表"""
        self.log_status("开始生成时间管理表...")
        
        try:
            # 使用子线程运行以避免阻塞UI
            threading.Thread(target=self._run_generate_timetable).start()
        except Exception as e:
            self.log_status(f"生成时间管理表时出错: {str(e)}")
    
    def _run_generate_timetable(self):
        """在子线程中运行生成时间管理表命令"""
        try:
            # 创建一个进程来运行generate_timetable.py
            process = subprocess.Popen(
                ["python", "generate_timetable.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 实时读取输出
            for line in process.stdout:
                line = line.strip()
                if line:
                    # 使用copy=True以使lambda捕获变量line的当前值
                    self.root.after(0, lambda line=line: self.log_status(f"生成时间表: {line}"))
            
            # 读取错误输出
            stderr_output, _ = process.communicate()
            if stderr_output:
                self.root.after(0, lambda: self.log_status(f"生成时间管理表出错: {stderr_output}"))
            
            # 等待进程结束
            exit_code = process.wait()
            if exit_code == 0:
                self.root.after(0, lambda: self.log_status("时间管理表生成成功"))
            else:
                self.root.after(0, lambda: self.log_status(f"生成时间管理表失败，退出码: {exit_code}"))
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda error_msg=error_msg: self.log_status(f"生成时间管理表时出错: {error_msg}"))
    
    def open_config_manager(self):
        """打开用户配置管理"""
        self.log_status("打开用户配置管理...")
        
        try:
            # 使用子进程运行配置管理器
            subprocess.Popen(["python", "config.py"])
        except Exception as e:
            error_msg = str(e)
            self.log_status(f"打开配置管理器出错: {error_msg}")
    
    def refresh_user_info(self):
        """刷新用户信息"""
        user = config.get_active_user()
        
        # 获取用户框架
        user_frame = None
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.LabelFrame) and subchild.cget("text") == "当前用户信息":
                        user_frame = subchild
                        break
        
        if user_frame:
            # 清除旧信息
            for widget in user_frame.winfo_children():
                widget.destroy()
            
            # 添加新信息
            ttk.Label(user_frame, text=f"用户名: {user['username']}").grid(row=0, column=0, padx=5, pady=5, sticky='w')
            ttk.Label(user_frame, text=f"城市: {user['city']}").grid(row=0, column=1, padx=5, pady=5, sticky='w')
            ttk.Label(user_frame, text=f"Bark Key: {user['bark_key'][:10]}...").grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')
            
            self.log_status(f"已刷新用户信息: {user['username']}")
        else:
            self.log_status("无法找到用户信息框架")
    
    def toggle_activity_monitor(self):
        """切换活动监控状态"""
        if self.activity_process is None:
            # 启动活动监控
            self.start_activity_monitor()
        else:
            # 停止活动监控
            self.stop_activity_monitor()
    
    def start_activity_monitor(self):
        """启动活动监控"""
        try:
            # 使用管道捕获输出，而不是新控制台窗口
            self.activity_process = subprocess.Popen(
                ["python", "current_activities.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # 不创建新窗口
            )
            
            # 创建子线程来读取输出
            self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self.stdout_thread.start()
            
            self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self.stderr_thread.start()
            
            self.log_status("活动监控已启动")
            self.monitor_button.config(text="停止活动监控")
        except Exception as e:
            error_msg = str(e)
            self.log_status(f"启动活动监控时出错: {error_msg}")
    
    def _read_stdout(self):
        """读取标准输出"""
        while self.activity_process and not self.activity_process.stdout.closed:
            try:
                line = self.activity_process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    # 使用lambda捕获变量当前值
                    self.root.after(0, lambda l=line: self.log_status(f"活动监控: {l}"))
            except:
                break
        
        # 进程结束后处理
        if self.activity_process:
            exit_code = self.activity_process.poll()
            if exit_code is not None:
                self.root.after(0, lambda c=exit_code: self.log_status(f"活动监控进程已退出，退出码: {c}"))
                self.activity_process = None
                self.root.after(0, lambda: self.monitor_button.config(text="启动活动监控"))
    
    def _read_stderr(self):
        """读取标准错误"""
        while self.activity_process and not self.activity_process.stderr.closed:
            try:
                line = self.activity_process.stderr.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    # 使用lambda捕获变量当前值
                    self.root.after(0, lambda l=line: self.log_status(f"活动监控错误: {l}"))
            except:
                break
        
        # 进程结束后处理
        if self.activity_process:
            exit_code = self.activity_process.poll()
            if exit_code is not None:
                self.root.after(0, lambda c=exit_code: self.log_status(f"活动监控进程已退出，退出码: {c}"))
                self.activity_process = None
                self.root.after(0, lambda: self.monitor_button.config(text="启动活动监控"))
    
    def stop_activity_monitor(self):
        """停止活动监控"""
        if self.activity_process:
            try:
                import signal
                self.log_status("正在发送停止信号到活动监控...")
                
                try:
                    # 在Windows上，需要特殊处理
                    if os.name == 'nt':
                        # 使用Windows特有的方法强制终止
                        import ctypes
                        CTRL_BREAK_EVENT = 1
                        ctypes.windll.kernel32.GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, self.activity_process.pid)
                    else:
                        # 在Unix/Linux上使用SIGINT
                        self.activity_process.send_signal(signal.SIGINT)
                        
                    self.log_status("已发送停止信号到活动监控")
                    
                    # 等待进程终止
                    try:
                        self.activity_process.wait(timeout=5)
                        self.log_status("活动监控已正常停止")
                    except subprocess.TimeoutExpired:
                        self.log_status("活动监控未响应停止信号，正在强制终止...")
                        self.activity_process.terminate()
                        self.log_status("活动监控已强制终止")
                except Exception as e:
                    self.log_status(f"发送停止信号时出错: {str(e)}")
                    self.log_status("正在尝试强制终止...")
                    self.activity_process.terminate()
                    self.log_status("活动监控已强制终止")
                
                # 重置进程状态
                self.activity_process = None
                self.monitor_button.config(text="启动活动监控")
                
            except Exception as e:
                error_msg = str(e)
                self.log_status(f"停止活动监控时出错: {error_msg}")
                
                # 确保进程被终止
                try:
                    if self.activity_process:
                        self.activity_process.kill()
                        self.activity_process = None
                        self.log_status("活动监控已强制终止")
                        self.monitor_button.config(text="启动活动监控")
                except Exception as e2:
                    error_msg = str(e2)
                    self.log_status(f"无法停止活动监控: {error_msg}")

def main():
    # 加载用户配置
    with open('user_config.json', 'r', encoding='utf-8') as f:
        user_config = json.load(f)
    
    for user_id, user in user_config['users'].items():
        if not user['enabled']:
            print(f"用户{user['username']}未启用，跳过")
            continue
        
        print(f"开始处理用户{user['username']}的活动...")
        # ... 调用current_activities等模块，传入user_id ...
    
    root = tk.Tk()
    app = TimeingManager(root)
    root.mainloop()

if __name__ == "__main__":
    main() 