import random
import json
import os

def arknights_endfield_character_rule(up_flag, six_star_remaining, four_star_streak_remaining):
    """
    明日方舟：终末地抽卡规则逻辑
    
    参数:
    up_flag: 是否触发强制大保底 (True/False)。
    total_current_pulls: 当前总计已投入的抽数 (用于判定 120 抽大保底)。
    six_star_remaining: 距离 80 抽必出六星角色的倒计时 (80 -> 1)。为 1 时必出六星。
    four_star_streak_remaining: 距离“强制不出四星”的倒计时 (10 -> 1)。为 1 时强制不出四星。
    
    输出:
    (rarity, arsenal_quota, guarantee_quota)
    """
    # 1. 输入合法性校验
    if not isinstance(six_star_remaining, int) or not (1 <= six_star_remaining <= 80):
        raise ValueError("参数 six_star_remaining 必须是 1 到 80 之间的整数")
    if not isinstance(four_star_streak_remaining, int) or not (1 <= four_star_streak_remaining <= 10):
        raise ValueError("参数 four_star_streak_remaining 必须是 1 到 10 之间的整数")

    # 2. 规则 120 抽大保底: 当 total_current_pulls 达到 119 (即第 120 抽) 且大保底未被消耗时，必出 UP
    rarity = None
    if up_flag:
        rarity = 'up_six'
    else:
        # 3. 计算六星概率 (规则 3)
        # 基础概率 0.8%
        p_six = 0.008
        if six_star_remaining == 1:
            p_six = 1.0
        elif six_star_remaining <= 15:
            # 每级提升 5%
            p_six = 0.008 + (16 - six_star_remaining) * 0.05
        
        # 4. 计算五星和四星概率 (规则 4)
        if four_star_streak_remaining == 1:
            # four_star_streak_remaining=1 时，四星概率为 0，五星概率提高
            p_four = 0.0
            p_five = max(0.0, 1.0 - p_six)
        else:
            # 通常情况
            # 规则 3 提到：y 提升时，四星降低，五星不变
            p_five = 0.08
            # 确保 p_six + p_five 不超过 1.0
            if p_six + p_five > 1.0:
                p_five = 1.0 - p_six
                p_four = 0.0
            else:
                p_four = 1.0 - p_six - p_five

        # 5. 抽取判定
        rand_val = random.random()
        
        if rand_val < p_six:
            # 六星判定：50% 概率为 up_six
            rarity = 'up_six' if random.random() < 0.5 else 'six'
        elif rand_val < p_six + p_five:
            rarity = 'five'
        else:
            rarity = 'four'

    # 定义武库配额和保障配额
    if rarity in ['up_six', 'six']:
        arsenal_quota = 2000
        guarantee_quota = 50
    elif rarity == 'five':
        arsenal_quota = 200
        guarantee_quota = 10
    else:  # four
        arsenal_quota = 20
        guarantee_quota = 0
        
    return rarity, arsenal_quota, guarantee_quota

# 全局缓存配置文件，避免重复读取
_POOL_CONFIG = None

def _get_pool_config():
    global _POOL_CONFIG
    if _POOL_CONFIG is None:
        pool_config_path = os.path.join(os.path.dirname(__file__), 'pool_config.json')
        with open(pool_config_path, 'r', encoding='utf-8') as f:
            _POOL_CONFIG = json.load(f)
    return _POOL_CONFIG

def arknights_endfield_execution(count, up_guarantee_available=True, total_current_pulls=0, six_star_remaining=80, four_star_streak_remaining=10):
    """
    抽卡执行函数
    
    参数:
    count: 抽卡次数
    up_guarantee_available: UP 保底是否可用
    total_current_pulls: 当前总计投入抽数
    six_star_remaining: 六星保底倒计时
    four_star_streak_remaining: 四星连续倒计时
    
    输出:
    (角色名列表, 更新后的 up_guarantee_available, 更新后的 total_current_pulls, 更新后的 six_star_remaining, 更新后的 four_star_streak_remaining, 累计武库配额, 累计保障配额)
    """
    # 获取卡池配置（使用缓存）
    pool_config = _get_pool_config()
    
    results = []
    total_arsenal_quota = 0
    total_guarantee_quota = 0
    up_flag = False
    
    for _ in range(count):

        # 1. 调用规则函数判定稀有度
        up_flag = up_guarantee_available and total_current_pulls == 119
        rarity, a_quota, g_quota = arknights_endfield_character_rule(up_flag, six_star_remaining, four_star_streak_remaining)
        
        # 累计配额
        total_arsenal_quota += a_quota
        total_guarantee_quota += g_quota
        
        # 2. 根据稀有度从池子中随机选择角色
        character_list = pool_config.get(rarity, [])
        character = random.choice(character_list)
        results.append(character)
        
        # 
        # 3. 更新计数器
        total_current_pulls += 1
        
        # UP 保底状态更新
        if rarity == 'up_six':
            up_guarantee_available = False
        
        # 六星保底倒计时逻辑
        if rarity in ['up_six', 'six']:
            six_star_remaining = 80
        else:
            six_star_remaining -= 1
            
        # 四星连续倒计时逻辑
        if rarity == 'four':
            four_star_streak_remaining -= 1
        else:
            four_star_streak_remaining = 10
        
        # 4. 触发卡池规则：30 抽赠送独立十连
        if total_current_pulls == 30:
            # 执行一次独立的 10 连抽
            # 此 10 连抽独立于主卡池状态，不计入 total_current_pulls，也不触发二次赠送
            bonus_results, _, _, _, _, bonus_a, bonus_g = arknights_endfield_execution(
                10, up_guarantee_available=False, total_current_pulls=0, six_star_remaining=80, four_star_streak_remaining=10
            )
            results.extend(bonus_results)
            total_arsenal_quota += bonus_a
            total_guarantee_quota += bonus_g
            
    return results, up_guarantee_available, total_current_pulls, six_star_remaining, four_star_streak_remaining, total_arsenal_quota, total_guarantee_quota

# 测试与验证代码
if __name__ == "__main__":
    import collections
    
    def run_test_execution(pull_count):
        print(f"\n--- 开始进行 {pull_count} 连抽测试 ---")
        
        # 获取池子配置用于统计
        pool_config = _get_pool_config()
        up_six_list = pool_config.get("up_six", [])
        six_list = pool_config.get("six", [])
        five_list = pool_config.get("five", [])
        
        # 初始状态
        results, up_avail, total_pulls, s_rem, f_rem, a_quota, g_quota = arknights_endfield_execution(
            pull_count, 
            up_guarantee_available=True, 
            total_current_pulls=10, 
            six_star_remaining=80, 
            four_star_streak_remaining=10
        )
        
        # 统计结果
        counts = collections.Counter(results)
        num_up_six = sum(counts[name] for name in up_six_list)
        num_six = sum(counts[name] for name in six_list)
        num_five = sum(counts[name] for name in five_list)
        num_four = len(results) - num_up_six - num_six - num_five
        
        print(f"抽卡汇总结果:")
        print(f"  - 总计获取角色数: {len(results)} (含可能的赠送角色)")
        print(f"  - UP 六星: {num_up_six}")
        print(f"  - 普通六星: {num_six} (总计六星: {num_up_six + num_six})")
        print(f"  - 五星角色: {num_five}")
        print(f"  - 四星角色: {num_four}")
        print(f"  - 累计武库配额: {a_quota}")
        print(f"  - 累计保障配额: {g_quota}")
        
        print(f"\n抽卡结束后更新的状态:")
        print(f"  - up_guarantee_available: {up_avail}")
        print(f"  - total_current_pulls: {total_pulls}")
        print(f"  - six_star_remaining: {s_rem}")
        print(f"  - four_star_streak_remaining: {f_rem}")

    # 执行 n 连抽测试 
    run_test_execution(50)
    
    # 也可以执行更多次测试
    # run_test_execution(10)
