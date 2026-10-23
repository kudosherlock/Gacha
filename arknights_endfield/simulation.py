import json
import os
import numpy as np
import matplotlib.pyplot as plt
try:
    from .gacha_model import arknights_endfield_execution
except ImportError:
    from gacha_model import arknights_endfield_execution

# 限定角色列表
LIMITED_CHARACTERS = ["莱万汀", "洁尔佩塔", "伊冯"]

def calculate_value(obtained_characters, total_final_pulls, initial_char_counts):
    """
    计算抽到的角色总价值
    规则：
    - 对于每一个限定角色：
        - 第 1 次抽到（含初始数量）：价值 100
        - 第 2-6 次抽到：价值 20
        - 第 7 次及以上：价值 10
    - 每满 240 抽额外赠送一个 UP 角色（一定是第 2 次或以后获取）
    """
    total_value = 0
    # 复制初始状态，用于本次模拟的累计
    current_counts = initial_char_counts.copy()
    
    # 计算额外赠送的 UP 角色数量
    bonus_up_count = total_final_pulls // 240
    
    # 先处理抽到的角色
    for char in obtained_characters:
        if char in LIMITED_CHARACTERS:
            current_counts[char] += 1
            count = current_counts[char]
            
            # 根据当前抽到的次数（含初始数量）计算价值
            if count == 1:
                total_value += 100
            elif 2 <= count <= 6:
                total_value += 20
            else:
                total_value += 10
    
    # 处理额外赠送的角色 (假定赠送的是列表中的第一个角色 "莱万汀")
    # 规则说：这个up角色一定是第2次或以后获取
    for _ in range(bonus_up_count):
        char = LIMITED_CHARACTERS[0]
        current_counts[char] += 1
        count = current_counts[char]
        if count == 1:
            # 理论上不会发生，因为 120 抽大保底已经保证了第一次
            total_value += 100
        elif 2 <= count <= 6:
            total_value += 20
        else:
            total_value += 10
                
    return total_value

def calculate_actual_pulls(spent_pulls, guarantee_quota, total_pulls_at_end):
    """
    计算实际抽数
    规则：
    1. 优惠抽数 = 保障配额 / 25
    2. 如果总抽取数 (total_pulls) >= 60，则优惠抽数再 + 10
    3. 实际抽数 = 花费抽数 - 优惠抽数
    """
    discount_pulls = guarantee_quota / 25
    if total_pulls_at_end >= 60:
        discount_pulls += 10
        
    actual_pulls = spent_pulls - discount_pulls
    return actual_pulls

def obtain_and_stop(target_characters, initial_status):
    """
    抽卡策略函数：抽出目标角色即停止
    
    规则：
    1. 每次抽 1 张卡，计入花费抽数。
    2. 抽出目标角色即停止。
    (卡池奖励逻辑已由底层 arknights_endfield_execution 处理)
    
    输出:
    (花费抽数, 获得的所有角色列表, 累计武库配额, 累计保障配额, 最终 up_guarantee_available, 最终 total_current_pulls, 最终 s_rem, 最终 f_rem)
    """
    up_guarantee_available = initial_status.get('up_guarantee_available', True)
    total_invested_pulls = initial_status.get('total_invested_pulls', 0)
    s_rem = initial_status.get('six_star_remaining', 80)
    f_rem = initial_status.get('four_star_streak_remaining', 10)
    
    spent_pulls = 0
    all_obtained_characters = []
    total_arsenal = 0
    total_guarantee = 0
    found = False
    
    current_total = total_invested_pulls

    while not found:
        # 每次调用执行 1 次主抽卡。底层会自动处理 30 抽时的赠送。
        results, up_guarantee_available, current_total, s_rem, f_rem, a_quota, g_quota = arknights_endfield_execution(
            1, up_guarantee_available, current_total, s_rem, f_rem
        )
        spent_pulls += 1
        all_obtained_characters.extend(results)
        total_arsenal += a_quota
        total_guarantee += g_quota
        
        # 检查本次获取的角色中是否包含目标
        for char in results:
            if char in target_characters:
                found = True
                break
                
    return spent_pulls, all_obtained_characters, total_arsenal, total_guarantee, up_guarantee_available, current_total, s_rem, f_rem

def fixed_pull_strategy(pull_count, initial_status):
    """
    固定抽数策略函数：只抽取固定的抽数
    
    规则：
    1. 每次单抽直到达到 pull_count。
    (卡池奖励逻辑已由底层 arknights_endfield_execution 处理)
    """
    up_guarantee_available = initial_status.get('up_guarantee_available', True)
    total_invested_pulls = initial_status.get('total_invested_pulls', 0)
    s_rem = initial_status.get('six_star_remaining', 80)
    f_rem = initial_status.get('four_star_streak_remaining', 10)
    
    spent_pulls = 0
    all_obtained_characters = []
    total_arsenal = 0
    total_guarantee = 0
    
    current_total = total_invested_pulls

    # 直接一次性执行 pull_count 次抽取
    results, up_guarantee_available, current_total, s_rem, f_rem, a_quota, g_quota = arknights_endfield_execution(
        pull_count, up_guarantee_available, current_total, s_rem, f_rem
    )
    
    spent_pulls = pull_count
    all_obtained_characters.extend(results)
    total_arsenal += a_quota
    total_guarantee += g_quota
        
    return spent_pulls, all_obtained_characters, total_arsenal, total_guarantee, up_guarantee_available, current_total, s_rem, f_rem

def run_simulation(n_simulations=1000, strategy_func=obtain_and_stop, strategy_args=None, inherit_pity=False, target_list=None):
    """
    运行抽卡模拟并生成统计结果
    
    参数:
    strategy_func: 策略函数 (obtain_and_stop 或 fixed_pull_strategy)
    strategy_args: 策略函数的额外参数 (如目标角色列表或固定抽数)
    inherit_pity: 是否继承上一次模拟的 six_star_remaining 和 four_star_streak_remaining
    target_list: 用于统计抽出概率的目标角色列表
    """
    if strategy_args is None:
        if strategy_func == fixed_pull_strategy:
            strategy_args = 40
        else:
            strategy_args = ["莱万汀"]
            
    if target_list is None:
        if isinstance(strategy_args, list):
            target_list = strategy_args
        else:
            target_list = ["莱万汀"]
            
    status_config_path = os.path.join(os.path.dirname(__file__), 'status_config.json')
    if not os.path.exists(status_config_path):
        initial_status = {
            "up_pity_remaining": 120,
            "six_star_remaining": 80,
            "four_star_streak_remaining": 10,
            "independent_pull_remaining": 30
        }
    else:
        with open(status_config_path, 'r', encoding='utf-8') as f:
            initial_status = json.load(f)
    
    strategy_name = strategy_func.__name__
    print(f"开始模拟 {n_simulations} 次，策略: {strategy_name}，参数: {strategy_args}，继承开关: {'开启' if inherit_pity else '关闭'}")
    
    spent_pulls_list = []
    total_sim_value = 0
    total_sim_actual_pulls = 0
    total_sim_arsenal = 0
    total_sim_guarantee = 0
    obtained_count = 0
    
    # 当前保底状态
    current_pity_status = initial_status.copy()
    
    for i in range(n_simulations):
        # 准备本次模拟的输入状态
        sim_input_status = {}
        
        # 规则：up_guarantee_available 始终从 status_config.json 读取初始配置 (不跨模拟继承)
        sim_input_status['up_guarantee_available'] = initial_status.get('up_guarantee_available', True)
        # 规则：total_invested_pulls 始终从 status_config.json 读取初始配置 (不跨模拟继承)
        sim_input_status['total_invested_pulls'] = initial_status.get('total_invested_pulls', 0)
        
        if i > 0 and inherit_pity:
            # 继承模式：仅继承 six_star_remaining 和 four_star_streak_remaining
            sim_input_status['six_star_remaining'] = current_pity_status['six_star_remaining']
            sim_input_status['four_star_streak_remaining'] = current_pity_status['four_star_streak_remaining']
        else:
            # 非继承模式或第一轮：使用配置文件中的 pity 计数
            sim_input_status['six_star_remaining'] = initial_status.get('six_star_remaining', 80)
            sim_input_status['four_star_streak_remaining'] = initial_status.get('four_star_streak_remaining', 10)
        
        # 执行指定的策略
        spent, chars, arsenal, guarantee, final_up_avail, final_total_pulls, final_s_rem, final_f_rem = strategy_func(strategy_args, sim_input_status)
        
        if inherit_pity:
            # 记录本次结束状态供下一轮继承 (仅 pity 计数)
            current_pity_status['six_star_remaining'] = final_s_rem
            current_pity_status['four_star_streak_remaining'] = final_f_rem
        
        # 统计数据
        spent_pulls_list.append(spent)
        initial_char_counts = initial_status.get('initial_char_counts', {})
        total_sim_value += calculate_value(chars, final_total_pulls, initial_char_counts)
        total_sim_actual_pulls += calculate_actual_pulls(spent, guarantee, final_total_pulls)
        total_sim_arsenal += arsenal
        total_sim_guarantee += guarantee
        
        # 统计抽出目标次数 (仅针对固定抽数策略)
        if strategy_name == "fixed_pull_strategy":
            # 检查是否抽到了目标角色 (包括 240 抽赠送)
            has_target = any(c in target_list for c in chars)
            if not has_target:
                bonus_count_start = initial_status.get('total_invested_pulls', 0) // 240
                bonus_count_end = final_total_pulls // 240
                if bonus_count_end > bonus_count_start and LIMITED_CHARACTERS[0] in target_list:
                    has_target = True
            if has_target:
                obtained_count += 1
        
        if (i + 1) % (n_simulations // 10) == 0:
            print(f"进度: {((i + 1) / n_simulations) * 100:.0f}%")

    # 统计分析
    avg_spent = np.mean(spent_pulls_list)
    var_spent = np.var(spent_pulls_list)
    max_spent = np.max(spent_pulls_list)
    value_per_pull = total_sim_value / total_sim_actual_pulls if total_sim_actual_pulls != 0 else 0
    
    print("\n--- 统计结果 ---")
    print(f"花费抽数均值: {avg_spent:.2f}")
    print(f"花费抽数方差: {var_spent:.2f}")
    print(f"花费抽数最大值: {max_spent}")
    print(f"总价值: {total_sim_value}")
    print(f"总实际抽数: {total_sim_actual_pulls:.2f}")
    print(f"每一抽的价值数 (总价值/总实际抽数): {value_per_pull:.4f}")
    print(f"保障配额期望: {total_sim_guarantee / n_simulations:.2f}")
    print(f"武库配额期望: {total_sim_arsenal / n_simulations:.2f}")

    if strategy_name == "fixed_pull_strategy":
        obtained_pct = (obtained_count / n_simulations) * 100
        print(f"抽出目标占比: {obtained_pct:.2f}%")
        print(f"没抽出目标占比: {100 - obtained_pct:.2f}%")
    
    # 生成直方图
    plt.figure(figsize=(10, 6))
    plt.hist(spent_pulls_list, bins=range(min(spent_pulls_list), max_spent + 2), alpha=0.7, color='orange', edgecolor='black')
    plt.axvline(avg_spent, color='red', linestyle='dashed', linewidth=2, label=f'Mean: {avg_spent:.2f}')
    plt.title(f'Gacha Simulation: {strategy_name} (N={n_simulations})')
    plt.xlabel('Spent Pulls')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    plt.savefig(f'gacha_{strategy_name}_result.png')
    print(f"\n统计图已保存为 'gacha_{strategy_name}_result.png'")
    # plt.show()

if __name__ == "__main__":
    # 策略 1: 抽出目标角色即停止 (inherit_pity 默认为 False)
    target_list = ["汤汤"]
    # target_list = ["莱万汀", "洁尔佩塔", "伊冯"]
    run_simulation(n_simulations=1000000, strategy_func=obtain_and_stop, strategy_args=target_list, inherit_pity=False)
    
    # 策略 2: 固定抽数策略 (inherit_pity 默认为 True)
    # fixed_count = 10 # status_config.json中如果设置了免费十连/二十连，则需要修改
    # target_list = ["伊冯"]
    # run_simulation(n_simulations=100000, strategy_func=fixed_pull_strategy, strategy_args=fixed_count, inherit_pity=False, target_list=target_list)
    
