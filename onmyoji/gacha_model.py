import random
import json
import os

# 全局缓存配置文件，避免重复读取
_POOL_CONFIG = None
_UP_PROB_CONFIG = None

def _get_pool_config():
    global _POOL_CONFIG
    if _POOL_CONFIG is None:
        pool_config_path = os.path.join(os.path.dirname(__file__), 'pool_config.json')
        if not os.path.exists(pool_config_path):
            raise FileNotFoundError(f"配置文件未找到: {pool_config_path}")
        with open(pool_config_path, 'r', encoding='utf-8') as f:
            _POOL_CONFIG = json.load(f)
    return _POOL_CONFIG

def _get_up_prob_config():
    global _UP_PROB_CONFIG
    if _UP_PROB_CONFIG is None:
        up_prob_config_path = os.path.join(os.path.dirname(__file__), 'up_prob_config.json')
        if not os.path.exists(up_prob_config_path):
            raise FileNotFoundError(f"配置文件未找到: {up_prob_config_path}")
        with open(up_prob_config_path, 'r', encoding='utf-8') as f:
            _UP_PROB_CONFIG = json.load(f)
    return _UP_PROB_CONFIG

def onmyoji_gacha_rule(pity_remaining):
    """
    阴阳师抽卡规则函数
    
    参数:
    pity_remaining: 保底剩余数 (<= 60)，为 1 时触发保底
    
    输出:
    rarity: 字符串类型 ('UR', 'SP', 'SSR', 'SR', 'R')
    """
    
    # 基础概率
    # R: 78.65%, SR: 20%, SSR: 1%, SP: 0.25%, UR: 0.1%
    p_ur = 0.001
    p_sp = 0.0025
    p_ssr = 0.01
    p_sr = 0.20
    p_r = 0.7865
    
    # 保底逻辑
    if pity_remaining == 1:
        # 当保底剩余数为 1 时，抽到 SR, R, UR 的概率降为 0
        # 抽到 SP, SSR 的概率等比例放大
        # 原比例 SP:SSR = 0.25:1 = 1:4
        # 新概率 SP = 20%, SSR = 80%
        p_ur = 0.0
        p_sr = 0.0
        p_r = 0.0
        p_sp = 0.20
        p_ssr = 0.80
    
    rand_val = random.random()
    
    rarity = None
    
    # 判定稀有度
    # 累积概率区间判断
    current_threshold = 0.0
    
    # UR
    current_threshold += p_ur
    if rand_val < current_threshold:
        return 'UR'
        
    # SP
    current_threshold += p_sp
    if rand_val < current_threshold:
        rarity = 'SP'
        
    # SSR
    if rarity is None:
        current_threshold += p_ssr
        if rand_val < current_threshold:
            rarity = 'SSR'
            
    # SR
    if rarity is None:
        current_threshold += p_sr
        if rand_val < current_threshold:
            return 'SR'
            
    # R (剩下所有情况)
    if rarity is None:
        return 'R'
            
    return rarity

def onmyoji_execution(total_pulls, pity_countdown, up_config_name, is_up_prob_active=True):
    """
    抽卡执行函数
    
    参数:
    total_pulls: 当前卡池总计投入抽数
    pity_countdown: 保底倒计时
    up_config_name: UP概率配置文件组名 (如 'full_collection_sp')
    is_up_prob_active: UP概率是否生效 (True/False)
    
    输出:
    (角色名列表, 更新后的 total_pulls, 更新后的 pity_countdown, 更新后的 is_up_prob_active)
    """
    
    current_up_prob = 0.0
    
    # 1. 获取 UP 概率
    if is_up_prob_active:
        up_prob_config = _get_up_prob_config()
        steps = up_prob_config.get(up_config_name, [])
        
        # 查找当前 total_pulls 对应的概率区间
        # 假设 steps 是按 min 从小到大排序的
        for step in steps:
            if step['min'] <= total_pulls <= step['max']:
                current_up_prob = step['prob']
                break
            
        # 如果没找到配置，默认概率为 0
        if not steps and up_config_name:
            current_up_prob = 0.0
    else:
        # UP 概率失效，强制为 0
        current_up_prob = 0.0
        
    # 2. 调用抽卡规则
    rarity = onmyoji_gacha_rule(pity_countdown)
    
    # 3. 处理 UP 逻辑
    actual_rarity = rarity
    if is_up_prob_active and rarity in ['SP', 'SSR']:
        if random.random() < current_up_prob:
            actual_rarity = 'up_character'
            # 抽到 UP 角色，后续 UP 概率失效
            is_up_prob_active = False
    
    # 4. 获取角色
    pool_config = _get_pool_config()
    
    # 动态调整卡池逻辑
    # 获取 UP 角色列表
    up_char_list = pool_config.get('up_character', [])
    
    # 获取基础 SP 和 SSR 列表
    # 注意：pool_config.get('SP') 获取的是完整列表（包含可能存在的 UP 角色）
    full_sp_list = pool_config.get('SP', [])
    full_ssr_list = pool_config.get('SSR', [])
    
    final_char_list = []
    
    if is_up_prob_active:
        # UP 生效时：
        # 'up_character' -> 仅从 up_char_list 中选
        # 'SP' -> 从 full_sp_list 中剔除 UP 角色
        # 'SSR' -> 从 full_ssr_list 中剔除 UP 角色
        if actual_rarity == 'up_character':
            final_char_list = up_char_list
        elif actual_rarity == 'SP':
            final_char_list = [c for c in full_sp_list if c not in up_char_list]
            if not final_char_list: # 防御性编程：防止剔除后为空
                final_char_list = full_sp_list
        elif actual_rarity == 'SSR':
            final_char_list = [c for c in full_ssr_list if c not in up_char_list]
            if not final_char_list: # 防御性编程
                final_char_list = full_ssr_list
        else:
            final_char_list = pool_config.get(actual_rarity, [])
    else:
        # UP 失效时：
        # 'up_character' -> 不可能出现 (actual_rarity 不会是 up_character)
        # 'SP' -> 使用完整列表 full_sp_list (包含 UP 角色)
        # 'SSR' -> 使用完整列表 full_ssr_list (包含 UP 角色)
        
        if actual_rarity == 'up_character':
            # 这种情况只在 刚刚触发UP并把状态置为False 时发生
            final_char_list = up_char_list
        elif actual_rarity == 'SP':
            final_char_list = full_sp_list
        elif actual_rarity == 'SSR':
            final_char_list = full_ssr_list
        else:
            final_char_list = pool_config.get(actual_rarity, [])

    if not final_char_list:
        # 如果列表为空，返回一个占位符
        character = f"Unknown-{actual_rarity}"
    else:
        character = random.choice(final_char_list)
        
    results = [character]
    
    # 5. 更新计数器
    total_pulls += 1
    
    # 保底更新逻辑
    # 阴阳师规则：60 抽必出 SP/SSR。如果在 60 抽之前出了 SP/SSR，则重置。
    # 这里 up_character 本质也是 SP/SSR，所以也要重置。
    if actual_rarity in ['up_character', 'SP', 'SSR']:
        pity_countdown = 60
    else:
        pity_countdown -= 1
        if pity_countdown < 1:
            # 理论上 onmyoji_gacha_rule 在 pity_remaining=1 时必出 SP/SSR
            # 所以这里不应该减到 0，除非配置或逻辑有误，强制重置防死循环
            pity_countdown = 60
            
    return results, total_pulls, pity_countdown, is_up_prob_active

if __name__ == "__main__":
    # 简单的测试
    print("开始测试阴阳师抽卡...")
    
    # 初始状态
    t_pulls = 0
    p_count = 60
    config_name = "full_collection_sp"
    up_active = True
    
    # 模拟 100 抽
    for i in range(100):
        res, t_pulls, p_count, up_active = onmyoji_execution(t_pulls, p_count, config_name, up_active)
        # 仅打印抽到高稀有度的结果，避免刷屏
        char_name = res[0]
        
        # 我们可以通过 p_count 是否重置为 60 来判断是否出货
        if p_count == 60:
             print(f"第 {t_pulls} 抽: {char_name} (保底重置) [UP生效: {up_active}]")
        elif i % 10 == 0:
             # 每10抽打印一次进度
             pass
             
    print(f"测试结束。当前总抽数: {t_pulls}, 当前保底: {p_count}, UP状态: {up_active}")
