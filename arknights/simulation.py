import json
import os
import numpy as np
import matplotlib.pyplot as plt
try:
    from .gacha_model import arknights_execution, _get_pool_config
except ImportError:
    from gacha_model import arknights_execution, _get_pool_config

def calculate_value(obtained_characters, initial_char_counts):
    """
    计算抽到的角色总价值
    规则：
    - 对于每一个普通六星角色：
        - 第 1 次抽到：价值 100
        - 第 2-6 次抽到：价值 20
    - 对于每一个限定角色：
        - 第 1 次抽到：价值 200
        - 第 2-6 次抽到：价值 40
    - 第 7 次及以上抽到不增加价值
    """
    total_value = 0
    current_counts = initial_char_counts.copy()
    pool_config = _get_pool_config()
    limited_chars = pool_config.get("limited", [])
    six_chars = pool_config.get("six", [])
    
    for char in obtained_characters:
        if char in limited_chars:
            current_counts[char] = current_counts.get(char, 0) + 1
            count = current_counts[char]
            if count == 1:
                total_value += 200
            elif 2 <= count <= 6:
                total_value += 40
        elif char in six_chars:
            current_counts[char] = current_counts.get(char, 0) + 1
            count = current_counts[char]
            if count == 1:
                total_value += 100
            elif 2 <= count <= 6:
                total_value += 20
                
    return total_value

def obtain_and_stop(target_characters, initial_status):
    """
    抽卡策略函数：抽出目标角色即停止
    """
    six_star_pity_count = initial_status.get('six_star_pity_count', 0)
    ten_pull_guarantee_remaining = initial_status.get('ten_pull_guarantee_remaining', 10)
    
    spent_pulls = 0
    all_obtained_characters = []
    found = False
    
    while not found:
        results, six_star_pity_count, ten_pull_guarantee_remaining = arknights_execution(
            1, six_star_pity_count, ten_pull_guarantee_remaining
        )
        spent_pulls += 1
        all_obtained_characters.extend(results)
        
        for char in results:
            if char in target_characters:
                found = True
                break
                
    return spent_pulls, all_obtained_characters, six_star_pity_count, ten_pull_guarantee_remaining

def fixed_pull_strategy(pull_count, initial_status):
    """
    固定抽数策略函数：只抽取固定的抽数
    """
    six_star_pity_count = initial_status.get('six_star_pity_count', 0)
    ten_pull_guarantee_remaining = initial_status.get('ten_pull_guarantee_remaining', 10)
    
    results, six_star_pity_count, ten_pull_guarantee_remaining = arknights_execution(
        pull_count, six_star_pity_count, ten_pull_guarantee_remaining
    )
    
    spent_pulls = pull_count
    all_obtained_characters = results
        
    return spent_pulls, all_obtained_characters, six_star_pity_count, ten_pull_guarantee_remaining

def run_simulation(n_simulations=1000, strategy_func=obtain_and_stop, strategy_args=None, inherit_pity=False, target_list=None):
    if strategy_args is None:
        if strategy_func == fixed_pull_strategy:
            strategy_args = 40
        else:
            strategy_args = ["凯尔希·思衡托"]
            
    if target_list is None:
        if isinstance(strategy_args, list):
            target_list = strategy_args
        else:
            target_list = ["凯尔希·思衡托"]
            
    status_config_path = os.path.join(os.path.dirname(__file__), 'status_config.json')
    if not os.path.exists(status_config_path):
        initial_status = {
            "six_star_pity_count": 0,
            "ten_pull_guarantee_remaining": 10,
            "initial_char_counts": {}
        }
    else:
        with open(status_config_path, 'r', encoding='utf-8') as f:
            initial_status = json.load(f)
    
    strategy_name = strategy_func.__name__
    print(f"开始模拟 {n_simulations} 次，策略: {strategy_name}，参数: {strategy_args}，继承开关: {'开启' if inherit_pity else '关闭'}")
    
    spent_pulls_list = []
    total_sim_value = 0
    obtained_count = 0
    
    # 新增：用于统计 target_list 中每个角色的总出现次数
    target_char_counts = {char: 0 for char in target_list}
    
    current_pity_status = initial_status.copy()
    
    for i in range(n_simulations):
        sim_input_status = {}
        
        if i > 0 and inherit_pity:
            sim_input_status['six_star_pity_count'] = current_pity_status['six_star_pity_count']
            sim_input_status['ten_pull_guarantee_remaining'] = current_pity_status['ten_pull_guarantee_remaining']
        else:
            sim_input_status['six_star_pity_count'] = initial_status.get('six_star_pity_count', 0)
            sim_input_status['ten_pull_guarantee_remaining'] = initial_status.get('ten_pull_guarantee_remaining', 10)
        
        spent, chars, final_s_pity, final_ten_guarantee = strategy_func(strategy_args, sim_input_status)
        
        if inherit_pity:
            current_pity_status['six_star_pity_count'] = final_s_pity
            current_pity_status['ten_pull_guarantee_remaining'] = final_ten_guarantee
        
        spent_pulls_list.append(spent)
        initial_char_counts = initial_status.get('initial_char_counts', {})
        total_sim_value += calculate_value(chars, initial_char_counts)
        
        # 统计本轮 target_list 中各个角色的出现次数
        for char in chars:
            if char in target_char_counts:
                target_char_counts[char] += 1
        
        if strategy_name == "fixed_pull_strategy":
            has_target = any(c in target_list for c in chars)
            if has_target:
                obtained_count += 1
        
        if (i + 1) % max(1, (n_simulations // 10)) == 0:
            print(f"进度: {((i + 1) / n_simulations) * 100:.0f}%")

    avg_spent = np.mean(spent_pulls_list)
    var_spent = np.var(spent_pulls_list)
    max_spent = np.max(spent_pulls_list)
    total_sim_actual_pulls = sum(spent_pulls_list)
    value_per_pull = total_sim_value / total_sim_actual_pulls if total_sim_actual_pulls != 0 else 0
    
    print("\n--- 统计结果 ---")
    print(f"花费抽数均值: {avg_spent:.2f}")
    print(f"花费抽数方差: {var_spent:.2f}")
    print(f"花费抽数最大值: {max_spent}")
    print(f"总价值: {total_sim_value}")
    print(f"每一抽的价值数 (总价值/总实际抽数): {value_per_pull:.4f}")

    if strategy_name == "fixed_pull_strategy":
        obtained_pct = (obtained_count / n_simulations) * 100
        print(f"抽出目标占比 (至少抽出其中之一): {obtained_pct:.2f}%")
        print(f"没抽出目标占比: {100 - obtained_pct:.2f}%")
        
        print("\n--- 目标角色出现次数期望 ---")
        for char, count in target_char_counts.items():
            expected_count = count / n_simulations
            print(f"{char}: {expected_count:.4f} 次/仿真")
    
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

if __name__ == "__main__":
    target_list = ["凯尔希·思衡托", "可露希尔", "维什戴尔", "荒芜拉普兰德", "新约能天使"]
    pull_count = 300
    run_simulation(n_simulations=10000, strategy_func=fixed_pull_strategy, strategy_args=pull_count, inherit_pity=False, target_list=target_list)
    # run_simulation(n_simulations=10000, strategy_func=obtain_and_stop, strategy_args=target_list, inherit_pity=False)
