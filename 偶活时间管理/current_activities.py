import sqlite3
from datetime import datetime
import requests
import urllib.parse
import time
import signal
import sys
import os
import json

# 强制立即刷新输出
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 引入配置模块
from config import get_active_user, get_activities_by_city

# 定义全局变量，用于控制程序循环
running = True

# 处理信号
def signal_handler(sig, frame):
    global running
    signal_name = "未知"
    if sig == signal.SIGINT:
        signal_name = "SIGINT (Ctrl+C)"
    elif sig == signal.SIGTERM:
        signal_name = "SIGTERM"
    elif hasattr(signal, 'SIGBREAK') and sig == signal.SIGBREAK:
        signal_name = "SIGBREAK (Ctrl+Break)"
    
    print(f'\n检测到信号 {signal_name}，程序将在当前循环结束后退出...')
    sys.stdout.flush()
    running = False

# 注册所有可能的终止信号
def register_signals():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGBREAK'):  # Windows特有
        signal.signal(signal.SIGBREAK, signal_handler)

def get_current_activities():
    """查询当前正在进行的活动，根据当前用户配置筛选城市"""
    # 获取当前活动用户配置
    user = get_active_user()
    user_city = user['city']
    print(f"当前用户: {user['username']}, 所在城市: {user_city}")
    sys.stdout.flush()
    
    # 获取当前时间
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M")
    
    # 根据城市获取活动
    current_activities = get_activities_by_city(user_city, current_time)
    
    # 如果没有活动，返回信息
    if not current_activities:
        print(f"{user_city}当前没有正在进行的活动")
        sys.stdout.flush()
        return None
    
    # 连接数据库，获取每个活动的下一个团体
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    
    # 获取每个活动的下一个团体
    result = []
    for activity in current_activities:
        # 数据库结构是 (event_name, group_name, start_time, end_time, city, venue)
        event_name = activity[0]
        group_name = activity[1]
        start_time = activity[2]
        end_time = activity[3]
        
        # 获取当前活动的所有团体按时间排序
        cursor.execute("""
            SELECT group_name, start_time 
            FROM activities 
            WHERE event_name = ?
            ORDER BY start_time
        """, (event_name,))
        
        all_groups = cursor.fetchall()
        
        # 查找当前团体在排序后的列表中的位置
        current_index = -1
        for i, (g_name, g_start) in enumerate(all_groups):
            if g_name == group_name and g_start == start_time:
                current_index = i
                break
        
        # 获取下一个团体，如果当前是最后一个则返回"无"
        next_group_name = "无"
        next_start_time = "无"
        if current_index != -1 and current_index < len(all_groups) - 1:
            next_group_name = all_groups[current_index + 1][0]
            next_start_time = all_groups[current_index + 1][1].split()[1]  # 只取时间部分
        
        # 添加到结果列表，但不打印详细信息
        result.append({
            'event_name': event_name,
            'group_name': group_name,
            'start_time': start_time.split()[1],  # 只取时间部分
            'end_time': end_time.split()[1],  # 只取时间部分
            'next_group': next_group_name,
            'next_start_time': next_start_time
        })
    
    # 关闭数据库连接
    conn.close()
    
    return result

def format_output(activities):
    """格式化输出结果"""
    if not activities:
        return
    
    print("\n当前正在进行的活动:")
    
    for i, activity in enumerate(activities):
        if i > 0:
            print()
        
        # 只打印关键信息，不重复
        print(f"活动: {activity['event_name']}")
        print(f"当前: {activity['group_name']} ({activity['start_time']}-{activity['end_time']})")
        
        # 简化下一个团体的显示
        if activity['next_group'] != "无":
            print(f"下一个: {activity['next_group']} ({activity['next_start_time']}开始)")
        else:
            print("下一个: 无")
    
    sys.stdout.flush()

def send_to_bark(activities):
    """使用Bark将活动信息发送到手机"""
    if not activities:
        return
    
    # 获取当前用户的Bark Key
    user = get_active_user()
    bark_key = user['bark_key']
    
    for activity in activities:
        try:
            # 构建推送内容
            event_name = activity['event_name']
            group_name = activity['group_name']
            end_time = activity['end_time']  # 已经只有时间部分了
            next_group = activity['next_group']
            next_start_time = activity['next_start_time']
            
            # 构建完整URL - 直接在URL中使用中文，Bark会自动处理编码
            # 标题使用活动名称
            title = f"{event_name}"
            
            # 正文使用当前团体和下一个团体信息
            body = f"{group_name} ({activity['start_time']}-{end_time})"
            
            # 添加下一个团体信息
            if next_group != "无":
                body += f"\n下一个: {next_group} ({next_start_time})"
            
            # URL编码
            encoded_title = urllib.parse.quote(title)
            encoded_body = urllib.parse.quote(body)
            encoded_group = urllib.parse.quote(event_name)  # 使用活动名作为分组名
            
            # 构建URL
            url = f"https://api.day.app/{bark_key}/{encoded_title}/{encoded_body}?group={encoded_group}"
            
            # 发送请求，设置超时时间
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"已推送 {event_name} 到Bark")
                sys.stdout.flush()
            else:
                print(f"推送到Bark失败: {response.status_code}")
                sys.stdout.flush()
        except requests.exceptions.RequestException as e:
            print(f"网络错误，推送失败: {str(e)}")
            sys.stdout.flush()
        except Exception as e:
            print(f"推送失败: {str(e)}")
            sys.stdout.flush()
        
        # 多个推送之间稍作延迟
        time.sleep(1)

def main_loop():
    """主循环，每5分钟运行一次查询"""
    # 注册信号处理函数
    register_signals()
    
    try:
        # 尝试导入requests库 
        import requests
    except ImportError:
        print("错误: 缺少requests库，请先安装: pip install requests")
        sys.stdout.flush()
        return
    
    # 加载用户配置
    with open('user_config.json', 'r', encoding='utf-8') as f:
        user_config = json.load(f)
        
    print(f"活动监控已启动")
    sys.stdout.flush()
    
    while running:
        # 获取当前时间
        now = datetime.now()
        print(f"\n*** {now.strftime('%Y-%m-%d %H:%M:%S')} 开始检查活动 ***")
        sys.stdout.flush()
        
        for user_id, user in user_config['users'].items():
            if not user['enabled']:
                print(f"用户{user['username']}未启用，跳过")
                sys.stdout.flush()
                continue
            
            print(f"开始处理用户{user['username']}...")
            sys.stdout.flush()
            
            # 获取当前用户的活动
            activities = query_activities(user_id)
            
            if activities:
                # 如果有活动数据，打印到控制台
                format_output(activities)
                sys.stdout.flush()
                
                try:
                    # 推送活动数据到用户的Bark应用
                    push_activities(user_id, activities)  
                    sys.stdout.flush()
                except Exception as e:
                    print(f"推送到Bark时出现错误: {str(e)}")
                    sys.stdout.flush()
            else:
                print(f"{user['username']}当前没有正在进行的活动")
                sys.stdout.flush()
        
        # 等待5分钟，每秒检查一次是否需要退出
        print(f"下次检查将在5分钟后进行...")
        sys.stdout.flush()
        for i in range(5 * 60):
            if not running:
                break
            time.sleep(1)
            # 每分钟输出一个心跳，保持流畅
            if i > 0 and i % 60 == 0:
                remaining_minutes = (5*60-i)//60
                print(f"剩余{remaining_minutes}分钟到下次检查")
                sys.stdout.flush()
    
    print("程序已安全退出。")
    sys.stdout.flush()

def query_activities(user_id):
    with open('user_config.json', 'r', encoding='utf-8') as f:
        user_config = json.load(f)
    user = user_config['users'][user_id]
    
    # 获取用户所在城市
    user_city = user['city']
    print(f"当前用户: {user['username']}, 所在城市: {user_city}")
    sys.stdout.flush()
    
    # 获取当前时间
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M")
    
    # 根据城市获取活动
    current_activities = get_activities_by_city(user_city, current_time)
    
    # 如果没有活动，返回信息
    if not current_activities:
        print(f"{user_city}当前没有正在进行的活动")
        sys.stdout.flush()
        return None
    
    # 连接数据库，获取每个活动的下一个团体
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    
    # 获取每个活动的下一个团体
    result = []
    for activity in current_activities:
        # 数据库结构是 (event_name, group_name, start_time, end_time, city, venue)
        event_name = activity[0]
        group_name = activity[1]
        start_time = activity[2]
        end_time = activity[3]
        
        # 获取当前活动的所有团体按时间排序
        cursor.execute("""
            SELECT group_name, start_time 
            FROM activities 
            WHERE event_name = ?
            ORDER BY start_time
        """, (event_name,))
        
        all_groups = cursor.fetchall()
        
        # 查找当前团体在排序后的列表中的位置
        current_index = -1
        for i, (g_name, g_start) in enumerate(all_groups):
            if g_name == group_name and g_start == start_time:
                current_index = i
                break
        
        # 获取下一个团体，如果当前是最后一个则返回"无"
        next_group_name = "无"
        next_start_time = "无"
        if current_index != -1 and current_index < len(all_groups) - 1:
            next_group_name = all_groups[current_index + 1][0]
            next_start_time = all_groups[current_index + 1][1].split()[1]  # 只取时间部分
        
        # 添加到结果列表，但不打印详细信息
        result.append({
            'event_name': event_name,
            'group_name': group_name,
            'start_time': start_time.split()[1],  # 只取时间部分
            'end_time': end_time.split()[1],  # 只取时间部分
            'next_group': next_group_name,
            'next_start_time': next_start_time
        })
    
    # 关闭数据库连接
    conn.close()
    
    return result

def push_activities(user_id, activities):
    with open('user_config.json', 'r', encoding='utf-8') as f:  
        user_config = json.load(f)
    user = user_config['users'][user_id]
    
    # 获取用户的Bark推送设置
    bark_key = user['bark_key']
    
    for activity in activities:
        try:
            # 构建推送内容
            event_name = activity['event_name']
            group_name = activity['group_name']
            end_time = activity['end_time']  # 已经只有时间部分了
            next_group = activity['next_group']
            next_start_time = activity['next_start_time']
            
            # 构建完整URL - 直接在URL中使用中文，Bark会自动处理编码
            # 标题使用活动名称
            title = f"{event_name}"
            
            # 正文使用当前团体和下一个团体信息
            body = f"{group_name} ({activity['start_time']}-{end_time})"
            
            # 添加下一个团体信息
            if next_group != "无":
                body += f"\n下一个: {next_group} ({next_start_time})"
            
            # URL编码
            encoded_title = urllib.parse.quote(title)
            encoded_body = urllib.parse.quote(body)
            encoded_group = urllib.parse.quote(event_name)  # 使用活动名作为分组名
            
            # 构建URL
            url = f"https://api.day.app/{bark_key}/{encoded_title}/{encoded_body}?group={encoded_group}"
            
            # 打印URL，方便调试
            print(f"推送URL: {url}")
            sys.stdout.flush()
            
            # 发送请求，设置超时时间
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"已推送 {event_name} 到Bark")
                sys.stdout.flush()
            else:
                print(f"推送到Bark失败: {response.status_code}")
                sys.stdout.flush()
        except requests.exceptions.RequestException as e:
            print(f"网络错误，推送失败: {str(e)}")
            sys.stdout.flush()
        except Exception as e:
            print(f"推送失败: {str(e)}")
            sys.stdout.flush()
        
        # 多个推送之间稍作延迟
        time.sleep(1)

if __name__ == "__main__":
    main_loop() 