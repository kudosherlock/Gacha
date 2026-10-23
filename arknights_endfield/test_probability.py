import numpy as np
import matplotlib.pyplot as plt
import random
try:
    from .gacha_model import arknights_endfield_character_rule
except ImportError:
    from gacha_model import arknights_endfield_character_rule

def simulate_one_six_star():
    """
    模拟直到抽到一个六星，返回所需的抽数。
    """
    six_star_remaining = 80
    four_star_streak_remaining = 10
    pulls = 0
    while True:
        pulls += 1
        # arknights_endfield_character_rule(up_flag, six_star_remaining, four_star_streak_remaining)
        rarity, _, _ = arknights_endfield_character_rule(False, six_star_remaining, four_star_streak_remaining)
        
        if rarity in ['up_six', 'six']:
            return pulls
        
        # 更新状态 (参考 arknights_sim.py 的逻辑)
        six_star_remaining -= 1
        if rarity == 'four':
            four_star_streak_remaining -= 1
        else:
            four_star_streak_remaining = 10
            
        if six_star_remaining < 1:
            # 理论上不会发生，因为 six_star_remaining == 1 时概率为 1.0
            return pulls

def run_probability_simulation(n_simulations=1000000):
    print(f"开始运行 {n_simulations} 次模拟...")
    pull_counts = []
    for i in range(n_simulations):
        pull_counts.append(simulate_one_six_star())
        if (i + 1) % (n_simulations // 10) == 0:
            print(f"进度: {((i + 1) / n_simulations) * 100:.0f}%")
    
    return np.array(pull_counts)

def get_theoretical_probs():
    """
    计算每一抽的理论边际概率 P(X=n | X > n-1)
    """
    probs = []
    for n in range(1, 81):
        six_star_remaining = 80 - (n - 1)
        if six_star_remaining == 1:
            p = 1.0
        elif six_star_remaining <= 15:
            p = 0.008 + (16 - six_star_remaining) * 0.05
        else:
            p = 0.008
        probs.append(p)
    return np.array(probs)

def main():
    n_sims = 500000  # 50万次模拟足够看到平滑的曲线
    pull_counts = run_probability_simulation(n_sims)
    
    # 计算模拟的边际概率
    # P(n) = (在第 n 抽出的次数) / (还没在 n-1 抽出的总次数)
    max_pulls = 80
    empirical_probs = []
    remaining_sims = len(pull_counts)
    
    for n in range(1, max_pulls + 1):
        count_at_n = np.sum(pull_counts == n)
        if remaining_sims > 0:
            prob = count_at_n / remaining_sims
        else:
            prob = 0
        empirical_probs.append(prob)
        remaining_sims -= count_at_n
        
    theoretical_probs = get_theoretical_probs()
    
    # 绘图
    plt.figure(figsize=(12, 6))
    x = np.arange(1, max_pulls + 1)
    
    plt.plot(x, theoretical_probs, label='Theoretical Probability', color='blue', linestyle='--', alpha=0.8)
    plt.scatter(x, empirical_probs, label='Simulated Probability', color='red', s=10, alpha=0.5)
    
    plt.title('Arknights Endfield Gacha: 6-Star Marginal Probability')
    plt.xlabel('Pull Number (since last 6-star)')
    plt.ylabel('Probability')
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.legend()
    
    # 标注 65 抽的位置
    plt.axvline(x=65, color='green', linestyle=':', label='Pity Start (65)')
    
    # 限制 y 轴范围以便观察 0.8% 的区域
    # plt.ylim(0, 0.2) 
    
    plt.savefig('probability_comparison.png')
    print("模拟完成，对比曲线已保存为 'probability_comparison.png'")
    
    # 打印一些关键点的数值
    print(f"\n关键点对比:")
    print(f"{'Pull':<6} | {'Theory':<10} | {'Simulated':<10}")
    print("-" * 35)
    for n in [1, 65, 66, 70, 75, 80]:
        print(f"{n:<6} | {theoretical_probs[n-1]:<10.4f} | {empirical_probs[n-1]:<10.4f}")

if __name__ == "__main__":
    main()
