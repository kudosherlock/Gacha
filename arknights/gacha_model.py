import random
import json
import os

_POOL_CONFIG = None

def _get_pool_config():
    global _POOL_CONFIG
    if _POOL_CONFIG is None:
        pool_config_path = os.path.join(os.path.dirname(__file__), 'pool_config.json')
        with open(pool_config_path, 'r', encoding='utf-8') as f:
            _POOL_CONFIG = json.load(f)
    return _POOL_CONFIG

def arknights_character_rule(six_star_pity_count, ten_pull_guarantee_remaining):
    """
    计算出本次抽取的稀有度
    """
    p_six = 0.02
    if six_star_pity_count >= 50:
        p_six = 0.02 + (six_star_pity_count - 50 + 1) * 0.02
        p_six = min(1.0, p_six)
    
    p_five = 0.08
    p_four = 0.50
    p_three = 0.40
    
    if ten_pull_guarantee_remaining == 1:
        # 第十抽且前九抽没出五星或以上，则本次必定是五星或以上
        p_four = 0.0
        p_three = 0.0
        p_five = max(0.0, 1.0 - p_six)
    else:
        if p_six + p_five > 1.0:
            p_five = 1.0 - p_six
            p_four = 0.0
            p_three = 0.0
        elif p_six + p_five + p_four > 1.0:
            p_four = 1.0 - p_six - p_five
            p_three = 0.0
        else:
            p_three = 1.0 - p_six - p_five - p_four

    rand_val = random.random()
    if rand_val < p_six:
        return 'six'
    elif rand_val < p_six + p_five:
        return 'five'
    elif rand_val < p_six + p_five + p_four:
        return 'four'
    else:
        return 'three'

def select_character(rarity, pool_config):
    if rarity == 'six':
        rules = pool_config.get("six_star_special_rules", {})
        rate_up_prob = rules.get("rate_up_probability", 0.70)
        rate_up_chars = rules.get("rate_up_characters", ["凯尔希·思衡托", "可露希尔"])
        high_weight_chars = rules.get("high_weight_characters", ["维什戴尔", "荒芜拉普兰德", "新约能天使"])
        high_weight_val = rules.get("high_weight_value", 5)
        normal_weight_val = rules.get("normal_weight_value", 1)
        
        rand_val = random.random()
        if rand_val < rate_up_prob and rate_up_chars:
            return random.choice(rate_up_chars)
        else:
            # 获取所有六星（合并限定和普通六星），并去重
            all_six_stars = list(set(pool_config.get("limited", []) + pool_config.get("six", [])))
            # 排除掉 rate_up_chars
            available_chars = [c for c in all_six_stars if c not in rate_up_chars]
            
            if not available_chars:
                return random.choice(rate_up_chars) if rate_up_chars else None
                
            # 计算权重
            weights = []
            for c in available_chars:
                if c in high_weight_chars:
                    weights.append(high_weight_val)
                else:
                    weights.append(normal_weight_val)
                    
            total_weight = sum(weights)
            if total_weight == 0:
                return random.choice(available_chars)
                
            rand_w = random.uniform(0, total_weight)
            current_w = 0
            for c, w in zip(available_chars, weights):
                current_w += w
                if rand_w <= current_w:
                    return c
            return available_chars[-1]
    elif rarity == 'five':
        rules = pool_config.get("five_star_special_rules", {})
        rate_up_prob = rules.get("rate_up_probability", 0.50)
        rate_up_chars = rules.get("rate_up_characters", ["裂响"])
        
        rand_val = random.random()
        if rand_val < rate_up_prob and rate_up_chars:
            return random.choice(rate_up_chars)
        else:
            five_pool = [c for c in pool_config.get("five", []) if c not in rate_up_chars]
            if not five_pool:
                return random.choice(rate_up_chars) if rate_up_chars else None
            return random.choice(five_pool)
    elif rarity == 'four':
        return random.choice(pool_config.get("four", []))
    else:
        return random.choice(pool_config.get("three", []))

def arknights_execution(count, six_star_pity_count=0, ten_pull_guarantee_remaining=10):
    """
    抽卡执行函数
    
    参数:
    count: 抽卡次数
    six_star_pity_count: 当前已经连续未出六星的次数
    ten_pull_guarantee_remaining: 距离前十抽必出五星及以上的倒数
    
    输出:
    (角色名列表, 更新后的 six_star_pity_count, 更新后的 ten_pull_guarantee_remaining)
    """
    pool_config = _get_pool_config()
    results = []
    
    for _ in range(count):
        rarity = arknights_character_rule(six_star_pity_count, ten_pull_guarantee_remaining)
        character = select_character(rarity, pool_config)
        results.append(character)
        
        if rarity == 'six':
            six_star_pity_count = 0
            ten_pull_guarantee_remaining = 0 # 五星及以上已出
        elif rarity == 'five':
            six_star_pity_count += 1
            ten_pull_guarantee_remaining = 0 # 五星及以上已出
        else:
            six_star_pity_count += 1
            if ten_pull_guarantee_remaining > 0:
                ten_pull_guarantee_remaining -= 1
            elif ten_pull_guarantee_remaining == 0:
                # 只有在 > 0 时才减。如果等于 0 意味着前十抽已出或已过前十抽，不需要做任何事情
                pass
                
    return results, six_star_pity_count, ten_pull_guarantee_remaining

if __name__ == "__main__":
    import collections
    
    def run_test_execution(pull_count):
        print(f"\n--- 开始进行 {pull_count} 连抽测试 ---")
        
        results, s_pity, ten_guarantee = arknights_execution(
            pull_count, 
            six_star_pity_count=0, 
            ten_pull_guarantee_remaining=10
        )
        
        counts = collections.Counter(results)
        
        print(f"抽卡汇总结果:")
        print(f"  - 总计获取角色数: {len(results)}")
        
        rules_six = _get_pool_config().get("six_star_special_rules", {})
        for c in rules_six.get("rate_up_characters", []):
            print(f"  - {c} (UP): {counts.get(c, 0)}")
        for c in rules_six.get("high_weight_characters", []):
            print(f"  - {c} (高权重): {counts.get(c, 0)}")
            
        rules_five = _get_pool_config().get("five_star_special_rules", {})
        for c in rules_five.get("rate_up_characters", []):
            print(f"  - {c} (五星UP): {counts.get(c, 0)}")
        
        print(f"\n抽卡结束后更新的状态:")
        print(f"  - six_star_pity_count: {s_pity}")
        print(f"  - ten_pull_guarantee_remaining: {ten_guarantee}")

    run_test_execution(100)
