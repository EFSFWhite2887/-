import os
import json
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# 配置文件路径
CONFIG_FILE = 'user_config.json'

# 默认配置
DEFAULT_CONFIG = {
    'users': [
        {
            'username': '默认用户',
            'bark_key': 'N',
            'city': '广州'
        }
    ],
    'active_user': 0  # 默认选中的用户索引
}

def load_config():
    """加载配置文件，如果不存在则创建默认配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件出错: {str(e)}")
            return DEFAULT_CONFIG
    else:
        # 创建默认配置文件
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存配置文件出错: {str(e)}")
        return False

def get_active_user():
    """获取当前激活的用户配置"""
    with open('user_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    active_user_id = str(config['active_user'])
    
    if active_user_id in config['users']:
        return config['users'][active_user_id]
    else:
        # active_user无效，返回第一个用户的配置
        first_user_id = list(config['users'].keys())[0]
        return config['users'][first_user_id]

def get_all_cities():
    """从数据库中获取所有城市"""
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT city FROM activities ORDER BY city")
        cities = [row[0] for row in cursor.fetchall()]
        return cities
    except Exception as e:
        print(f"查询城市出错: {str(e)}")
        return []
    finally:
        conn.close()

def get_activities_by_city(city, current_time=None):
    """获取指定城市中正在进行的活动"""
    if not current_time:
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM activities 
            WHERE city = ? AND start_time <= ? AND end_time > ?
            ORDER BY event_name
        """, (city, current_time, current_time))
        
        return cursor.fetchall()
    except Exception as e:
        print(f"查询活动出错: {str(e)}")
        return []
    finally:
        conn.close()

class ConfigManager:
    def __init__(self, root):
        self.root = root
        self.root.title("用户配置管理")
        self.root.geometry("600x600")  # 将初始高度设置为600
        self.root.minsize(600, 600)  # 设置窗口最小尺寸为(600, 600)
        
        self.config = load_config()
        self.create_widgets()
        self.load_user_list()
    
    def create_widgets(self):
        # 创建标签框架
        self.frame = ttk.LabelFrame(self.root, text="用户管理")
        self.frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 创建用户列表(表格)
        self.user_tree = ttk.Treeview(self.frame, columns=('username', 'city'), show='headings')
        self.user_tree.heading('username', text='用户名')
        self.user_tree.heading('city', text='城市')
        self.user_tree.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky='nsew')
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.user_tree.yview)
        scrollbar.grid(row=0, column=3, sticky='ns')
        self.user_tree.configure(yscrollcommand=scrollbar.set)
        
        # 详细信息框
        self.details_frame = ttk.LabelFrame(self.frame, text="用户详情")
        self.details_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')
        
        # 用户名
        ttk.Label(self.details_frame, text="用户名:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.username_var = tk.StringVar()
        ttk.Entry(self.details_frame, textvariable=self.username_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Bark Key
        ttk.Label(self.details_frame, text="Bark Key:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.bark_key_var = tk.StringVar()
        ttk.Entry(self.details_frame, textvariable=self.bark_key_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # 城市
        ttk.Label(self.details_frame, text="城市:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.city_var = tk.StringVar()
        self.city_combobox = ttk.Combobox(self.details_frame, textvariable=self.city_var, width=20)
        self.city_combobox.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # 加载城市列表
        cities = get_all_cities()
        self.city_combobox['values'] = cities
        
        # 启用状态
        ttk.Label(self.details_frame, text="启用:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.enabled_var = tk.BooleanVar()
        ttk.Checkbutton(self.details_frame, variable=self.enabled_var).grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        # 按钮区域
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')
        
        ttk.Button(button_frame, text="添加新用户", command=self.add_user).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="保存", command=self.update_user).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="删除用户", command=self.delete_user).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="设为默认", command=self.set_default).grid(row=0, column=3, padx=5, pady=5)
        
        # 测试区域
        test_frame = ttk.LabelFrame(self.root, text="测试当前用户配置")
        test_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(test_frame, text="显示当前城市活动", command=self.show_current_activities).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(test_frame, text="测试Bark推送", command=self.test_bark).grid(row=0, column=1, padx=5, pady=5)
        
        # 绑定表格选择事件
        self.user_tree.bind('<<TreeviewSelect>>', self.on_user_select)
        
        # 设置权重以便调整大小
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
    
    def load_user_list(self):
        """加载用户列表"""
        # 清空表格
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        
        with open('user_config.json', 'r', encoding='utf-8') as f:
            user_config = json.load(f)
        
        for user_id, user in user_config['users'].items():
            self.user_tree.insert('', 'end', values=(user['username'], user['city']), tags=(user_id,))
        
        # 默认选中第一个用户
        if len(user_config['users']) > 0:
            self.user_tree.focus(self.user_tree.get_children()[0])
            self.user_tree.selection_set(self.user_tree.get_children()[0])
    
    def on_user_select(self, event):
        """用户选择事件处理"""
        selected_item = self.user_tree.focus()
        if not selected_item:
            return
        
        user_id = self.user_tree.item(selected_item, 'tags')[0]
        user = self.config['users'][user_id]
        
        self.username_var.set(user['username'])
        self.bark_key_var.set(user['bark_key'])
        self.city_var.set(user['city'])
        self.enabled_var.set(user.get('enabled', True))
    
    def add_user(self):
        """添加新用户"""
        username = simpledialog.askstring("新用户", "请输入用户名:")
        if not username:
            return
        
        # 检查用户名是否已存在
        for user in self.config['users'].values():
            if user['username'] == username:
                messagebox.showerror("错误", "用户名已存在")
                return
        
        bark_key = simpledialog.askstring("新用户", "请输入Bark Key:")
        if not bark_key:
            bark_key = DEFAULT_CONFIG['users'][0]['bark_key']
        
        city = simpledialog.askstring("新用户", "请输入城市:")
        if not city:
            city = DEFAULT_CONFIG['users'][0]['city']
        
        new_user = {
            'username': username,
            'bark_key': bark_key,
            'city': city,
            'enabled': True
        }
        
        # 生成新的用户ID
        new_user_id = str(len(self.config['users']) + 1)
        
        # 将新用户添加到字典中
        self.config['users'][new_user_id] = new_user
        
        save_config(self.config)
        self.load_user_list()
        
        # 选中新添加的用户
        self.user_tree.selection_clear()
        self.user_tree.selection_set(tk.END)
        self.on_user_select(None)
    
    def update_user(self):
        """更新用户信息"""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择一个用户")
            return
        
        user_id = self.user_tree.item(selected_items[0], 'tags')[0]
        
        username = self.username_var.get()
        bark_key = self.bark_key_var.get()
        city = self.city_var.get()
        enabled = self.enabled_var.get()
        
        if not username:
            messagebox.showerror("错误", "用户名不能为空")
            return
        
        # 检查用户名是否与其他用户重复
        for uid, user in self.config['users'].items():
            if uid != user_id and user['username'] == username:
                messagebox.showerror("错误", "用户名已存在")
                return
        
        self.config['users'][user_id] = {
            'username': username,
            'bark_key': bark_key,
            'city': city,
            'enabled': enabled
        }
        
        save_config(self.config)
        self.load_user_list()
        messagebox.showinfo("成功", "用户信息已更新")
    
    def delete_user(self):
        """删除用户"""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择一个用户")
            return
        
        user_id = self.user_tree.item(selected_items[0], 'tags')[0]
        
        if len(self.config['users']) <= 1:
            messagebox.showerror("错误", "必须保留至少一个用户")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除用户 {self.config['users'][user_id]['username']} 吗?"):
            # 如果删除的是当前激活用户，重置激活用户为第一个
            if user_id == str(self.config['active_user']):
                self.config['active_user'] = list(self.config['users'].keys())[0]
            
            del self.config['users'][user_id]
            save_config(self.config)
            self.load_user_list()
            
            # 清空详情
            self.username_var.set("")
            self.bark_key_var.set("")
            self.city_var.set("")
    
    def set_default(self):
        """设置默认用户"""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择一个用户")
            return
        
        user_id = self.user_tree.item(selected_items[0], 'tags')[0]
        self.config['active_user'] = user_id
        save_config(self.config)
        self.load_user_list()
        messagebox.showinfo("成功", f"{self.config['users'][user_id]['username']} 已设为默认用户")
    
    def show_current_activities(self):
        """显示当前城市的活动"""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择一个用户")
            return
        
        user_id = self.user_tree.item(selected_items[0], 'tags')[0]
        user = self.config['users'][user_id]
        city = user['city']
        
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M")
        activities = get_activities_by_city(city, current_time)
        
        if not activities:
            messagebox.showinfo("结果", f"{city}当前没有正在进行的活动")
            return
        
        result = f"当前时间: {current_time}\n{city}正在进行的活动:\n\n"
        
        for activity in activities:
            event_name = activity[0]
            group_name = activity[1]
            end_time = activity[3].split()[1]  # 只显示时间部分
            
            result += f"活动: {event_name}\n"
            result += f"团体: {group_name}\n"
            result += f"结束时间: {end_time}\n"
            result += "-" * 30 + "\n"
        
        # 创建结果窗口
        result_window = tk.Toplevel(self.root)
        result_window.title(f"{city}当前活动")
        result_window.geometry("500x400")
        
        text = tk.Text(result_window, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, result)
        text.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(text, orient='vertical', command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
    
    def test_bark(self):
        """测试Bark推送"""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择一个用户")
            return
        
        import requests
        import urllib.parse
        
        user_id = self.user_tree.item(selected_items[0], 'tags')[0]
        user = self.config['users'][user_id]
        
        bark_key = user['bark_key']
        if not bark_key:
            messagebox.showerror("错误", "Bark Key不能为空")
            return
        
        title = "测试推送"
        body = f"这是一条测试消息\n用户名: {user['username']}\n城市: {user['city']}"
        
        # URL编码
        encoded_title = urllib.parse.quote(title)
        encoded_body = urllib.parse.quote(body)
        
        # 构建URL
        url = f"https://api.day.app/{bark_key}/{encoded_title}/{encoded_body}"
        
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                messagebox.showinfo("成功", "推送测试消息成功!")
            else:
                messagebox.showerror("错误", f"推送失败，状态码: {response.status_code}")
        except Exception as e:
            messagebox.showerror("错误", f"推送出错: {str(e)}")

def run_config_manager():
    """运行配置管理工具"""
    root = tk.Tk()
    app = ConfigManager(root)
    root.mainloop()

if __name__ == "__main__":
    run_config_manager() 