import gymnasium as gym
import numpy as np
import matplotlib.pyplot as plt
import pickle
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def print_success_rate(rewards_per_episode):
    """Calculate and print the success rate of the agent."""
    total_episodes = len(rewards_per_episode)
    success_count = np.sum(rewards_per_episode)
    success_rate = (success_count / total_episodes) * 100
    print(f"Success Rate: {success_rate:.2f}% ({int(success_count)} / {total_episodes} episodes)")
    return success_rate

def run(episodes, is_training=True, render=False):
    
    env = gym.make('FrozenLake-v1', map_name="8x8", is_slippery=True, 
                    render_mode='human' if render else None)

    if(is_training):
        q = np.zeros((env.observation_space.n, env.action_space.n)) # init a 64 x 4 array
    else:
        f = open('frozen_lake8x8.pkl', 'rb')
        q = pickle.load(f)
        f.close()
            
    # Optimized parameters with penalty system
    learning_rate_a = 0.88
    discount_factor_g = 0.95
    epsilon = 1
    epsilon_decay_rate = 0.00008
    rng = np.random.default_rng()
    step_penalty = -0.002
    hole_penalty = -2.2

    rewards_per_episode = np.zeros(episodes)
    
    found_goal = False 

    times_of_findgoal = 0

    for i in range(episodes):
        
        if found_goal and is_training:
            times_of_findgoal += 1
            if times_of_findgoal == 1:
                epsilon /= 2
                learning_rate_a /= 2 
            if times_of_findgoal == 2:
                epsilon = 0.0
                learning_rate_a = 0.01 
            
        state = env.reset()[0]  # states: 0 to 63, 0=top left corner,63=bottom right corner
        terminated = False      # True when fall in hole or reached goal
        truncated = False       # True when actions > 200
        raw_reward = 0          
        
        while(not terminated and not truncated):
            if is_training and rng.random() < epsilon:
                action = env.action_space.sample() # actions: 0=left,1=down,2=right,3=up
            else:
                action = np.argmax(q[state,:])

            new_state, raw_reward, terminated, truncated, _ = env.step(action)

            # Apply penalty system
            if terminated and raw_reward == 0:  # Fell in hole
                reward_update = hole_penalty
            elif not terminated:  # Still walking
                reward_update = step_penalty
            else: 
                reward_update = 1.0 # Reached goal (raw_reward = 1)

            if is_training:
                # Q-learning Update
                q[state,action] = q[state,action] + learning_rate_a * (
                    reward_update + discount_factor_g * np.max(q[new_state,:]) - q[state,action]
                )

            state = new_state
        
        if raw_reward == 1:
            found_goal = True
            rewards_per_episode[i] = 1
        else:
            rewards_per_episode[i] = 0

        if is_training and not found_goal:
            epsilon = max(epsilon - epsilon_decay_rate, 0)
            
        
        if is_training and epsilon == 0 and not found_goal:
            learning_rate_a = 0.01

    env.close()

    sum_rewards = np.zeros(episodes)
    for t in range(episodes):
        sum_rewards[t] = np.sum(rewards_per_episode[max(0, t-100):(t+1)])
    
    plt.plot(sum_rewards)
    plt.title(f'Frozen Lake 8x8 Training Success (Goal-Locked, Moving Avg 100)')
    plt.ylabel('Successes in Last 100 Episodes')
    plt.xlabel('Episode')
    plt.savefig('frozen_lake8x8.png')
    plt.close() 
    
    if is_training == False:
        print_success_rate(rewards_per_episode)

    if is_training:
        f = open("frozen_lake8x8.pkl","wb")
        pickle.dump(q, f)
        f.close()


if __name__ == '__main__':
    #run(15000, is_training=True, render=False)  
    run(1000, is_training=False, render=False)